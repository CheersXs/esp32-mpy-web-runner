# ESP32-C3 Web Runner —— 应用逻辑模块
#
# 与 main.py 的职责划分（2026-08-15，DEBUG_NOTES 二十三节）：
# main.py 只做两件事：1) 先连 WiFi（堆干净时初始化驱动）；2) 按"大模块最先"
# 顺序加载 web/runner/config/console（每个之间 gc.collect()），让 GC split-heap
# 峰值各落在最新鲜的堆里（避免 100K split 把 esp-idf 堆抢空 → wifi 数据通路饿死）。
# 本模块在堆已稳定后才被 import，其自身的 400+ 行代码才不至于让 web 导入时
# 预占用堆过线。
#
# 注：SSD1306 也在这里（_oled_init 内）延迟加载，理由同上。

import gc
import sys
import time
import socket

import c3_config as cfg

try:
    import asyncio
except ImportError:
    import uasyncio as asyncio

try:
    import network
except ImportError:
    network = None

HOST = '0.0.0.0'
PORT = cfg.SERVER_PORT

# ---- 全局状态 ----
STA = None
STA_STATUS = 'connecting'   # connecting | connected | failed
OLED = None

# 数据健康探针（DNS 版）：向网关发 UDP DNS 查询等回复。
# 失败态（DEBUG_NOTES 十九/二十一节）：status=1010 关联保持，但数据帧
# 双向全断 —— lwIP pbuf / wifi RX 缓冲池耗尽（实测死态下 UDP sendto 直接
# 报错，wifi 初始化报 "Expected to init 10 rx buffer, actual is 0"）。
# 判据：REPLY = 数据通；SNDERR（sendto 分配 pbuf 失败）= 数据断。
_PROBE_TIMEOUT_S = 1.5
# 连续多少次 SNDERR 才判定数据断（避免单次抖动误触发）
_PROBE_FAIL_LIMIT = 2
# 探针间隔（ms）—— 当前关闭（600s）；根因(导入顺序+split-heap)已修，作为兜底保留
_PROBE_INTERVAL_MS = 600000
# OLED 内存回收阈值（字节）：低于此值才 gc.collect()，避免每 2s 全量 GC
# 反复 stop-the-world 并持续扰动 heap 分配形态（见 _oled_refresh 注释）
_GC_THRESHOLD = 30 * 1024


async def _sleep_ms(ms):
    await asyncio.sleep_ms(ms)


# ---------- OLED ----------

def _oled_init():
    """初始化 OLED，失败不致命（不影响网络/Web）。

    ssd1306 在重模块导入之后再加载：DEBUG_NOTES 二十三节实测，顶层提前
    import ssd1306 会把 web(microdot) 导入时 GC split 从 64K 顶成 100K、
    GC 总堆 128K→164K → wifi 数据通路饿死。延迟加载后 128K 存活。
    """
    try:
        import ssd1306
    except ImportError:
        return None
    try:
        from machine import I2C, Pin
        i2c = I2C(0, scl=Pin(cfg.OLED_SCL), sda=Pin(cfg.OLED_SDA),
                  freq=400000)
        return ssd1306.SSD1306_I2C(cfg.OLED_WIDTH, cfg.OLED_HEIGHT,
                                   i2c, addr=cfg.OLED_ADDR)
    except Exception as e:
        print('[oled] init failed: %r' % (e,))
        return None


def _oled_text(oled, lines):
    if oled is None:
        return
    try:
        oled.fill(0)
        y = 0
        for line in lines[:5]:
            oled.text(str(line), 0, y)
            y += 8
        oled.show()
    except Exception:
        pass


def _oled_error(err):
    """把异常显示到 OLED（72x40：5 行 x 9 字符），便于无串口时定位。"""
    if OLED is None:
        return
    text = 'ERR ' + str(err)
    lines = [text[i:i + 9] for i in range(0, len(text), 9)][:5]
    _oled_text(OLED, lines)


def _log_error(msg):
    """持久化最新错误到 /error.log，方便 mpremote cat 查看（只保留最新一条）。"""
    try:
        with open('/error.log', 'w') as f:
            f.write(msg + '\n')
    except Exception:
        pass


def _oled_refresh():
    """按连接状态刷新 OLED。72x40：每行 8px，最多 5 行，每行 9 字符。"""
    global STA_STATUS
    ip = ''
    if STA is not None and STA.isconnected():
        try:
            ip = STA.ifconfig()[0]
        except Exception:
            ip = ''
    # 不强制每轮 GC：2026-08-15 起改为阈值触发（低于 _GC_THRESHOLD 才回收）。
    # 每 2s 全量 GC 会在单核 C3 上反复 stop-the-world，且持续扰动 heap 分配
    # 形态（观测到与"模块加载堆碎片冲击 WiFi 驱动"的失败态相关，见 DEBUG_NOTES
    # 二十节）。OLED 每轮只产生约 1KB 垃圾，留给需要时一次性回收即可。
    mem = gc.mem_free()
    if mem < _GC_THRESHOLD:
        gc.collect()
        mem = gc.mem_free()
    mem //= 1024
    ssid = cfg.WIFI_SSID
    if ip:
        # 连接成功：IP（分两行显示完整）+ Mem + SSID Online
        _oled_text(OLED, [
            'IP ' + ip[:6],
            ip[6:],
            'Mem %dK' % mem,
            ssid[:9] + ' On',
        ])
    else:
        # 连接中：Connecting + SSID + Mem
        _oled_text(OLED, [
            'Connecting',
            ssid[:9],
            'Mem %dK' % mem,
        ])


# ---------- 数据健康探针（DNS 版） ----------
#
# 失败态（DEBUG_NOTES 十九/二十一节）：status=1010 关联保持、isconnected()=True，
# 但数据帧双向全断 —— lwIP pbuf / wifi RX 缓冲池耗尽（实测死态下 UDP sendto 直接
# 报错、wifi 初始化报 "Expected to init 10 rx buffer, actual is 0"）。
# 判据：向网关发 UDP DNS 查询等回复。REPLY = 双向数据帧在走（活）；SNDERR =
# sendto 分配 pbuf 失败（死）；TO/NOREAD = 无法判定（不计死）。自连接探针
# （连本机 IP）已证实走 lwIP 内部环路、从不碰射频，废弃（二十一节）。


def _valid_ip4(s):
    try:
        parts = str(s).split('.')
        if len(parts) != 4:
            return False
        for p in parts:
            v = int(p)
            if v < 0 or v > 255:
                return False
        return True
    except Exception:
        return False


def _dns_query():
    pkt = b'\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00'
    pkt += b'\x01w\x00'
    pkt += b'\x00\x01\x00\x01'
    return pkt


def _dns_probe():
    """返回 'REPLY'/'SNDERR'/'NOREAD'/'TO'/'SKIP'。"""
    if STA is None:
        return 'SKIP'
    gw = ''
    try:
        if STA.isconnected():
            gw = STA.ifconfig()[2]
    except Exception:
        gw = ''
    if not _valid_ip4(gw):
        return 'SKIP'
    s = None
    try:
        import select
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setblocking(False)
        try:
            s.sendto(_dns_query(), (gw, 53))
        except Exception:
            return 'SNDERR'   # lwIP 无 pbuf 可发 = 数据断
        try:
            _, _, _ = select.select([s], [], [], _PROBE_TIMEOUT_S)
            try:
                s.recvfrom(512)
                return 'REPLY'
            except Exception:
                return 'NOREAD'
        except Exception:
            return 'TO'
    except Exception:
        return 'SKIP'
    finally:
        if s is not None:
            try:
                s.close()
            except Exception:
                pass


async def _rescue_data_path():
    """死态自救：一级轻量重连 → 二级 driver 硬复位 → 三级整机重启。

    实测：轻量重连(disconnect+connect)在死态下连不回去（pbuf 耗尽导致
    关联帧都发不出）；driver 硬复位(active False→True)偶尔有效；
    machine.reset() 必然清掉（代价是重启，且可能再次落入死态）。
    """
    print('[sta] DATA DEAD: rescue chain')
    # 一级：轻量重连（不碰驱动）
    try:
        STA.disconnect()
    except Exception:
        pass
    await _sleep_ms(800)
    try:
        STA.connect(cfg.WIFI_SSID, cfg.WIFI_PASS)
    except Exception as e:
        print('[sta] rescue-1 connect err %r' % (e,))
    for _ in range(20):
        if STA.isconnected():
            break
        await _sleep_ms(500)
    if STA.isconnected():
        try:
            STA.config(pm=0)
        except Exception:
            pass
        print('[sta] rescue-1 ok, reconnected ip=%s' % STA.ifconfig()[0])
        return
    # 二级：driver 硬复位
    print('[sta] rescue-1 failed, hard-reset driver')
    try:
        STA.active(False)
    except Exception:
        pass
    await _sleep_ms(1000)
    gc.collect()
    try:
        STA.active(True)
    except Exception as e:
        print('[sta] rescue-2 active err %r' % (e,))
    await _sleep_ms(1500)
    try:
        STA.connect(cfg.WIFI_SSID, cfg.WIFI_PASS)
    except Exception as e:
        print('[sta] rescue-2 connect err %r' % (e,))
    for _ in range(20):
        if STA.isconnected():
            break
        await _sleep_ms(500)
    if STA.isconnected():
        try:
            STA.config(pm=0)
        except Exception:
            pass
        print('[sta] rescue-2 ok, reconnected ip=%s' % STA.ifconfig()[0])
        return
    # 三级：整机重启
    print('[sta] rescue-2 failed, machine.reset()')
    try:
        with open('/last_rescue', 'w') as f:
            f.write(str(time.time()) + '\n')
    except Exception:
        pass
    await _sleep_ms(200)
    import machine
    machine.reset()


# ---------- STA（内联，非阻塞，asyncio 任务） ----------

async def _sta_task():
    """后台任务：维持 STA 连接，掉线后自动重连。不阻塞事件循环。

    注意：首次连接在 main.py 里同步完成（必须在加载重模块前、堆干净时做，
    否则 esp-idf 驱动分配失败）。这里只负责维持：掉线后 disconnect 再
    connect（已验证在模块加载后可行）。

    硬复位兜底：连续 3 次重连失败 → active(False)+gc+active(True) 重建无线
    驱动。用于自救"调试复位把射频搞残"的假死状态（扫描/关联丢失但 CPU 正常）。

    数据健康探针（2026-08-15 DNS 版）：关联在但数据断的失败态（DEBUG_NOTES
    十九/二十一节）isconnected() 恒 True，普通重连逻辑永远不触发。这里每
    _PROBE_INTERVAL_MS 向网关发 UDP DNS 查询，连续 _PROBE_FAIL_LIMIT 次
    SNDERR（sendto 分配 pbuf 失败）→ 判定数据断 → _rescue_data_path()
    三级自救（轻量重连 → driver 硬复位 → machine.reset()）。
    """
    global STA_STATUS
    fails = 0
    probe_fails = 0
    last_probe = time.ticks_ms()
    while True:
        if STA is not None and STA.isconnected():
            STA_STATUS = 'connected'
            fails = 0
            # 数据健康探针：关联在但数据断时 isconnected() 不反映问题，
            # 必须主动探测。只在连接稳定时探测。
            now = time.ticks_ms()
            if time.ticks_diff(now, last_probe) >= _PROBE_INTERVAL_MS:
                last_probe = now
                r = _dns_probe()
                if r == 'REPLY':
                    probe_fails = 0
                elif r == 'SNDERR':
                    probe_fails += 1
                    print('[sta] data probe SNDERR (%d/%d)' % (
                        probe_fails, _PROBE_FAIL_LIMIT))
                    if probe_fails >= _PROBE_FAIL_LIMIT:
                        probe_fails = 0
                        await _rescue_data_path()
                # TO / NOREAD / SKIP：无法判定，不计死也不清零
        else:
            STA_STATUS = 'connecting'
            print('[sta] reconnecting to %s ...' % cfg.WIFI_SSID)
            try:
                STA.disconnect()
            except Exception:
                pass
            for _ in range(20):
                if STA.status() != network.STAT_CONNECTING:
                    break
                await _sleep_ms(100)
            try:
                STA.connect(cfg.WIFI_SSID, cfg.WIFI_PASS)
            except Exception as e:
                print('[sta] connect error: %r' % (e,))
                STA_STATUS = 'failed'
            ok = False
            for _ in range(40):
                if STA.isconnected():
                    ok = True
                    STA_STATUS = 'connected'
                    print('[sta] connected, ip=%s' % STA.ifconfig()[0])
                    try:
                        STA.config(pm=0)
                    except Exception:
                        pass
                    break
                await _sleep_ms(500)
            if not ok:
                fails += 1
                STA_STATUS = 'failed'
                print('[sta] connect failed (%d)' % fails)
                if fails >= 3:
                    print('[sta] hard-reset wifi driver ...')
                    fails = 0
                    try:
                        STA.active(False)
                    except Exception:
                        pass
                    await _sleep_ms(1000)
                    gc.collect()
                    try:
                        STA.active(True)
                    except Exception:
                        pass
                    await _sleep_ms(1500)
        await _sleep_ms(3000)


# ---------- OLED 刷新任务 ----------

async def _oled_task():
    """每 2 秒刷新 OLED。"""
    while True:
        _oled_refresh()
        await _sleep_ms(2000)


# ---------- 启动 ----------

def run(sta):
    """main.py 在完成 WiFi 连接 + 重模块加载后调用本函数启动应用。"""
    global STA, OLED, STA_STATUS
    STA = sta

    import config
    import console
    import runner as runner_mod
    import web

    # C3 纯 STA：强制关闭 AP（即使 config.json 未预置也兜底）
    try:
        c = config.load()
        c['ap']['enabled'] = False
        config.save(c)
    except Exception:
        pass

    con = console.get_console().attach()
    con._push('== ESP32-C3 Web Runner ==')
    con._push(' mem %dK, wifi %s' % (gc.mem_free() // 1024, cfg.WIFI_SSID))

    OLED = _oled_init()
    _oled_text(OLED, ['ESP32-C3', 'wifi init...'])

    manager = runner_mod.Manager(con)
    hub = web.Hub(con)
    app = web.create_app(manager, hub)

    async def bootstrap():
        asyncio.create_task(_sta_task())
        asyncio.create_task(_oled_task())

        autostart = config.load().get('autostart', []) or []
        if autostart:
            manager.autostart(autostart)

        con._push('[web] listen :%d' % PORT)
        # start_server 失败绝不 return：一旦退出 asyncio.run，3 个后台任务
        # （喂狗/OLED/STA）会被全部取消，看门狗 10 秒后复位，陷入重启循环。
        # 改为：错误写 OLED + /error.log + 串口，5 秒后重试，期间事件循环保持存活。
        while True:
            gc.collect()
            try:
                await app.start_server(host=HOST, port=PORT, debug=False)
            except Exception as e:
                msg = '[web] 服务器启动失败: %r' % (e,)
                con._push(msg + '，5 秒后重试')
                _oled_error(e)
                _log_error(msg)
                for _ in range(25):
                    await _sleep_ms(200)
                continue
            con._push('[web] 服务器已停止')
            break

    try:
        asyncio.run(bootstrap())
    except KeyboardInterrupt:
        con._push('[web] 手动停止')
    except Exception as e:
        con._push('[web] 异常退出: %r' % (e,))
        try:
            import io as _io
            _buf = _io.StringIO()
            sys.print_exception(e, _buf)
            for _l in _buf.getvalue().rstrip('\n').split('\n'):
                con._push(_l)
        except Exception:
            pass
        try:
            sys.print_exception(e, sys.stdout)
        except Exception:
            pass
        import machine
        try:
            machine.reset()
        except Exception:
            pass
