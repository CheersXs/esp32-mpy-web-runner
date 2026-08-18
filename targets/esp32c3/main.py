# ESP32-C3 Web Runner —— 引导壳
#
# 职责（DEBUG_NOTES 二十三节，2026-08-15）：
# C3 固件是 split-heap，MicroPython GC 堆按需增长，每次 split 直接从 esp-idf
# 堆抢 64-100K 连续内存。若重模块（web→microdot）在堆近满时才导入，编译瞬态
# 峰值会撑爆 64K 初始堆、触发 100K split → esp-idf 被抢空 → wifi 数据通路饿死
# （"关联在数据断"，status=1010 但收发全断）。
#
# 对策（实测 web 最先导入 + 各 import 间 gc.collect() → GC 总堆停在 128K，
# 入站 28-29/30；坏顺序 164K，0-4/30）：
#   1) 先连 WiFi（驱动初始化必须在堆干净时）；
#   2) 大模块最先导入、小模块随后，每个之间 gc.collect()；
#   3) 本文件保持极薄（自身代码对象也占用预导入堆），应用逻辑全在 c3_app.py，
#      堆稳定后才 import。
# 顺序不可乱，改动需复测。

import gc
import sys
import time

import c3_config as cfg

try:
    import asyncio
except ImportError:
    import uasyncio as asyncio

try:
    import network
except ImportError:
    network = None

STA = None


def _wait_connect(sta, timeout_ms=30000):
    """阻塞等待 WiFi 连接成功（首次连接专用）。"""
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < timeout_ms:
        if sta.isconnected():
            return True
        time.sleep_ms(300)
    return False


def main():
    global STA

    gc.collect()

    # 1) 先初始化 WiFi 驱动并完成首次连接（需要连续内存 + 干净堆）。
    #    必须在加载重模块前做：web/runner 等大模块会占满/碎片化堆，
    #    之后 esp-idf 驱动分配 RX buffer 或握手内存会失败。
    if network is not None:
        STA = network.WLAN(network.STA_IF)
        STA.active(True)
        time.sleep_ms(500)
        print('[sta] connecting to %s ...' % cfg.WIFI_SSID)
        try:
            STA.connect(cfg.WIFI_SSID, cfg.WIFI_PASS)
        except Exception as e:
            print('[sta] connect error: %r' % (e,))
        if _wait_connect(STA):
            print('[sta] connected, ip=%s' % STA.ifconfig()[0])
            # 关键修复（2026-08-14 实测确认）：C3 固件默认 pm=1(modem-sleep)，
            # 空闲约 15s 后上行(板→AP)被省电机制杀掉 —— 板子"看起来连着"、
            # 下行正常(能收到 SYN/请求)，但 TX 响应全丢，入站永久等待。
            # STA.config(pm=0) 关省电后入站 200 毫秒级恢复。连上后立刻设置，
            # 重连任务里也会补设。
            try:
                STA.config(pm=0)
                print('[sta] pm=0 (modem-sleep off)')
            except Exception as e:
                print('[sta] pm set err: %r' % (e,))
        else:
            print('[sta] first connect failed (will keep retrying in bg)')

    # 2) WiFi 就绪后再加载重模块：最大的模块（web→microdot）最先，小模块随后，
    #    每个之间 gc.collect()，让各编译峰值各落在最新鲜的堆里。
    #    顺序固定为 web → runner → config → console（见 docs/C3_PORTING_GUIDE.md，
    #    顺序不可乱，插入任何模块都会挤占 split-heap 导入窗口 → wifi 数据通路饿死）。
    #    fsapi/fsmgr（v2.2.0 文件管理）不参与本序列：由 web.create_app() 在 GC
    #    堆稳定后延迟注册（fsapi.py 自身设计纪律，HEAD 真机验证安全）。
    import web
    gc.collect()
    import runner as runner_mod
    gc.collect()
    import config
    gc.collect()
    import console
    gc.collect()

    # 3) 堆稳定后加载应用逻辑（OLED / STA 维护 / Web 启动）。
    import c3_app
    c3_app.run(STA)


if __name__ == '__main__':
    main()
