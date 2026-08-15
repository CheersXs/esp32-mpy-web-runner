# main.py —— 启动 Web 服务器 + 程序调度器 + 看门狗
import sys
import gc

import config
import console
import net
import runner as runner_mod
import web

try:
    import asyncio
except ImportError:
    import uasyncio as asyncio

HOST = '0.0.0.0'
PORT = 80
WDT_TIMEOUT_MS = 5000
WDT_FEED_MS = 1500


def _setup_watchdog():
    wdt = None
    try:
        import machine
        wdt = machine.WDT(timeout=WDT_TIMEOUT_MS)
    except Exception as e:
        console.get_console()._push('[boot] 看门狗不可用: %r' % (e,))
    return wdt


async def _backlog_loop(wdt):
    while True:
        if wdt is not None:
            try:
                wdt.feed()
            except Exception:
                pass
        await asyncio.sleep_ms(WDT_FEED_MS)


def main():
    con = console.get_console().attach()

    cfg = config.load()

    con._push('*' * 46)
    con._push(' ESP32 Web Runner v%s 启动中...' % config.VERSION)
    con._push('*' * 46)

    netinfo = net.setup_network(cfg, con)
    if netinfo['ap_ip']:
        con._push('[net] AP  运行中  http://%s  (主机名:%s)' %
                  (netinfo['ap_ip'], cfg['ap'].get('ssid', 'ESP32-S3')))
    if netinfo['sta_connected']:
        con._push('[net] STA 已连接  http://%s  (ssid:%s)' %
                  (netinfo['sta_ip'], netinfo['sta_ssid']))
    elif netinfo['sta_ssid']:
        con._push('[net] STA 连接中 %r（后台线程，不影响启动）' %
                  netinfo['sta_ssid'])
    else:
        con._push('[net] STA 未连接（可在网页设置里配置 WiFi）')

    manager = runner_mod.Manager(con)
    hub = web.Hub(con)
    app = web.create_app(manager, hub)

    wdt = _setup_watchdog()

    async def bootstrap():
        asyncio.create_task(_backlog_loop(wdt))

        autostart = cfg.get('autostart', []) or []
        if autostart:
            manager.autostart(autostart)

        con._push('[web] 控制台: http://%s' %
                  (netinfo['ap_ip'] or netinfo['sta_ip']))
        try:
            await app.start_server(host=HOST, port=PORT, debug=False)
        except Exception as e:
            con._push('[web] 服务器启动失败: %r' % (e,))
            return
        while True:
            await asyncio.sleep_ms(60000)

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