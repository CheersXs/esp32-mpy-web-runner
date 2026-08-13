import time

try:
    import network
except ImportError:
    network = None

STA_TIMEOUT_MS = 15000


def _ap_enabled(cfg):
    return True


def setup_network(cfg):
    """启动 AP + STA。STA 连接为阻塞等待，适合在 boot 阶段调用。"""
    result = {'ap': None, 'sta': None, 'ap_ip': None, 'sta_ip': None,
              'sta_connected': False, 'sta_ssid': ''}
    if network is None:
        return result

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
    try:
        result['ap_ip'] = ap.ifconfig()[0]
    except Exception:
        result['ap_ip'] = '192.168.4.1'
    result['ap'] = ap

    wf = cfg.get('wifi', {}) or {}
    ssid = wf.get('ssid')
    if ssid:
        sta = network.WLAN(network.STA_IF)
        sta.active(True)
        try:
            sta.connect(ssid, wf.get('password') or '')
            t0 = time.ticks_ms()
            while not sta.isconnected():
                if time.ticks_diff(time.ticks_ms(), t0) > STA_TIMEOUT_MS:
                    break
                time.sleep_ms(200)
        except Exception:
            pass
        result['sta'] = sta
        result['sta_connected'] = bool(sta.isconnected())
        if result['sta_connected']:
            try:
                result['sta_ip'] = sta.ifconfig()[0]
            except Exception:
                pass
        result['sta_ssid'] = ssid
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
        ap_cfg = cfg.get('ap', {}) or {}
        essid = ap_cfg.get('ssid') or 'ESP32-S3'
        ap_pass = ap_cfg.get('password') or None
        try:
            ap = network.WLAN(network.AP_IF)
            ap.active(True)
            if ap_pass:
                ap.config(essid=essid, password=ap_pass,
                          authmode=network.AUTH_WPA_WPA2_PSK)
            else:
                ap.config(essid=essid)
        except Exception:
            pass

        wf = cfg.get('wifi', {}) or {}
        ssid = wf.get('ssid')
        sta = network.WLAN(network.STA_IF)
        sta.active(True)
        if sta.isconnected():
            sta.disconnect()
        if ssid:
            sta.connect(ssid, wf.get('password') or '')
            t0 = time.ticks_ms()
            while not sta.isconnected():
                if time.ticks_diff(time.ticks_ms(), t0) > STA_TIMEOUT_MS:
                    break
                time.sleep_ms(200)
            if sta.isconnected():
                if console:
                    console._push('[net] STA connected, ip=%s' %
                                  (sta.ifconfig()[0],))
            else:
                if console:
                    console._push('[net] STA connect failed for %r' % (ssid,))
        else:
            if console:
                console._push('[net] STA disabled (no ssid in config)')
    except Exception as e:
        if console:
            console._push('[net] reconfigure error: %r' % (e,))