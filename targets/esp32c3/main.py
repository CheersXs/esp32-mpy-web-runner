# ESP32-C3 Web Runner —— 纯 STA 模式 + 完整 Web IDE + OLED 本地状态屏
#
# 与 S3 版共享 lib/（config/console/runner/uvm/web/ssd1306），
# 差异点：
#   - 不发射 AP 热点（ap.enabled=false，纯 STA 连路由器）
#   - STA 连接逻辑内联（不依赖 net.py），便于 OLED 实时显示连接状态
#   - OLED 显示 IP / 内存 / 连接状态
#
# 配置在 c3_config.py（WiFi / OLED 引脚 / 端口）。

import gc
import sys
import time

import c3_config as cfg
import config
import console
import runner as runner_mod
import web

try:
    import asyncio
except ImportError:
    import uasyncio as asyncio

try:
    import network
except ImportError:
    network = None

try:
    import ssd1306
except ImportError:
    ssd1306 = None

HOST = '0.0.0.0'
PORT = cfg.SERVER_PORT
WDT_TIMEOUT_MS = 10000   # 长一点，避免首次连接慢导致误重启
WDT_FEED_MS = 2000

# ---- 全局状态 ----
STA = None
STA_STATUS = 'connecting'   # connecting | connected | failed
OLED = None


async def _sleep_ms(ms):
    await asyncio.sleep_ms(ms)


# ---------- OLED ----------

def _oled_init():
    """初始化 OLED，失败不致命（不影响网络/Web）。"""
    if ssd1306 is None:
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


def _oled_refresh():
    """按连接状态刷新 OLED。72x40：每行 8px，最多 5 行，每行 9 字符。"""
    global STA_STATUS
    ip = ''
    if STA is not None and STA.isconnected():
        try:
            ip = STA.ifconfig()[0]
        except Exception:
            ip = ''
    gc.collect()
    mem = gc.mem_free() // 1024
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


# ---------- STA（内联，非阻塞，asyncio 任务） ----------

async def _sta_task():
    """后台任务：确保 STA 已连接，失败自动重连。不阻塞事件循环。"""
    global STA_STATUS
    while True:
        if STA is not None and STA.isconnected():
            STA_STATUS = 'connected'
        else:
            STA_STATUS = 'connecting'
            print('[sta] connecting to %s ...' % cfg.WIFI_SSID)
            try:
                STA.connect(cfg.WIFI_SSID, cfg.WIFI_PASS)
            except Exception as e:
                print('[sta] connect error: %r' % (e,))
                STA_STATUS = 'failed'
            # 等待连接（最多 15 秒），期间让出事件循环，Web 服务器照常响应
            for _ in range(30):
                if STA.isconnected():
                    STA_STATUS = 'connected'
                    print('[sta] connected, ip=%s' % STA.ifconfig()[0])
                    break
                await _sleep_ms(500)
            if not STA.isconnected():
                STA_STATUS = 'failed'
                print('[sta] connect failed')
        await _sleep_ms(3000)


# ---------- OLED 刷新任务 ----------

async def _oled_task():
    """每 2 秒刷新 OLED。"""
    while True:
        _oled_refresh()
        await _sleep_ms(2000)


# ---------- 看门狗 ----------

async def _wdt_task():
    """看门狗喂狗，防止主循环卡死自动重启。"""
    wdt = None
    try:
        import machine
        wdt = machine.WDT(timeout=WDT_TIMEOUT_MS)
    except Exception as e:
        print('[wdt] unavailable: %r' % (e,))
    while True:
        if wdt is not None:
            try:
                wdt.feed()
            except Exception:
                pass
        await _sleep_ms(WDT_FEED_MS)


# ---------- 主流程 ----------

def main():
    global STA, OLED

    gc.collect()
    print('[boot] ESP32-C3 Web Runner start, mem_free=%d' % gc.mem_free())

    # C3 纯 STA：强制关闭 AP（即使 config.json 未预置也兜底）
    try:
        c = config.load()
        c['ap']['enabled'] = False
        config.save(c)
    except Exception:
        pass

    con = console.get_console().attach()
    con._push('*' * 46)
    con._push(' ESP32-C3 Web Runner 启动中...')
    con._push('*' * 46)

    OLED = _oled_init()
    _oled_text(OLED, ['ESP32-C3', 'wifi init...'])

    # 启动 STA（保持 active，不阻塞主流程）
    if network is not None:
        STA = network.WLAN(network.STA_IF)
        STA.active(True)

    manager = runner_mod.Manager(con)
    hub = web.Hub(con)
    app = web.create_app(manager, hub)

    async def bootstrap():
        asyncio.create_task(_sta_task())
        asyncio.create_task(_oled_task())
        asyncio.create_task(_wdt_task())

        autostart = config.load().get('autostart', []) or []
        if autostart:
            manager.autostart(autostart)

        con._push('[web] 控制台: http://<C3-IP>:%d' % PORT)
        try:
            await app.start_server(host=HOST, port=PORT, debug=False)
        except Exception as e:
            con._push('[web] 服务器启动失败: %r' % (e,))
            return
        while True:
            await _sleep_ms(60000)

    try:
        asyncio.run(bootstrap())
    except KeyboardInterrupt:
        con._push('[web] 手动停止')
    except Exception as e:
        con._push('[web] 异常退出: %r' % (e,))
        try:
            sys.print_exception(e, sys.stdout)
        except Exception:
            pass
        import machine
        try:
            machine.reset()
        except Exception:
            pass


if __name__ == '__main__':
    main()