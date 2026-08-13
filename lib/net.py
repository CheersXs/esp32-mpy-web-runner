import time

try:
    import network
except ImportError:
    network = None

STA_TIMEOUT_MS = 15000


def _ap_enabled(cfg):
    return True


def _apply_ap(cfg):
    """配置 AP，返回是否成功。"""
    if network is None:
        return False
    ap_cfg = cfg.get('ap', {}) or {}
    essid = ap_cfg.get('ssid') or 'ESP32-S3'
    ap_pass = ap_cfg.get('password') or None
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    try:
        if ap_pass:
            ap.config(essid=essid, password=ap_pass,
                      authmode=network.AUTH_WPA_WPA2_PSK)
        else:
            ap.config(essid=essid)
    except Exception:
        try:
            ap.config(essid=essid)
        except Exception:
            pass
    return True


def _connect_sta(cfg, console):
    """连接 STA（阻塞，最多等待 STA_TIMEOUT_MS）。失败不抛出。"""
    if network is None:
        return
    import config
    wf = cfg.get('wifi', {}) or {}
    ssid = wf.get('ssid')
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    if ssid:
        if console:
            console._push('[net] STA 连接中 %r ...' % (ssid,))
        try:
            sta.connect(ssid, wf.get('password') or '')
            t0 = time.ticks_ms()
            while not sta.isconnected():
                if time.ticks_diff(time.ticks_ms(), t0) > STA_TIMEOUT_MS:
                    break
                time.sleep_ms(200)
        except Exception:
            pass
    if sta.isconnected():
        if console:
            console._push('[net] STA 已连接, ip=%s' % (sta.ifconfig()[0],))
    else:
        if console:
            console._push('[net] STA 连接失败（或未配置 WiFi）')


def setup_network(cfg, console=None):
    """启动 AP + STA。AP 立即生效；STA 在后台线程连接，不阻塞启动。"""
    result = {'ap': None, 'sta': None, 'ap_ip': None, 'sta_ip': None,
              'sta_connected': False, 'sta_ssid': ''}
    if network is None:
        return result

    _apply_ap(cfg)
    try:
        ap = network.WLAN(network.AP_IF)
        result['ap_ip'] = ap.ifconfig()[0]
    except Exception:
        result['ap_ip'] = '192.168.4.1'
    result['ap'] = network.WLAN(network.AP_IF)
    result['sta'] = network.WLAN(network.STA_IF)

    wf = cfg.get('wifi', {}) or {}
    result['sta_ssid'] = wf.get('ssid') or ''
    try:
        sta = network.WLAN(network.STA_IF)
        result['sta_connected'] = bool(sta.active() and sta.isconnected())
        if result['sta_connected']:
            result['sta_ip'] = sta.ifconfig()[0]
    except Exception:
        pass

    if wf.get('ssid') and not result['sta_connected']:
        # 未连上：后台线程连接，不阻塞 boot，避免开机卡 15 秒
        try:
            import _thread
            _thread.start_new_thread(_connect_sta, (cfg, console))
        except Exception as e:
            if console:
                console._push('STA 后台连接启动失败: %r' % (e,))
    elif console and result['sta_connected']:
        console._push('[net] STA 已连接（开机自动恢复）')
    return result


def reconfigure(console):
    """网页保存配置后调用：在后台线程里重连 STA / 更新 AP。"""
    import _thread
    try:
        import config
        _thread.start_new_thread(_do_reconfigure, (console,))
    except Exception as e:
        if console:
            console._push('reconfigure error: %r' % (e,))


def _do_reconfigure(console):
    import config
    try:
        cfg = config.load()
        if console:
            console.flush()
            console._push('[net] applying new network config...')
        _apply_ap(cfg)
        _connect_sta(cfg, console)
    except Exception as e:
        if console:
            console._push('[net] reconfigure error: %r' % (e,))