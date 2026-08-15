"""Web 层：microdot 路由 + 静态文件 + REST API + WebSocket 实时控制台。"""

import gc
import os
import sys
import time

try:
    import json
except ImportError:
    import ujson as json

try:
    import asyncio
except ImportError:
    import uasyncio as asyncio

from microdot.microdot import Microdot, Response, Request

import config

WWW_DIR = '/www'
CM_DIR = WWW_DIR + '/cm'

ASYNC_TEMPLATE = """#type:async
# 板上可开关的异步程序（可被网页随时停止）
import uvm
import machine

led = machine.Pin(2, machine.Pin.OUT)   # 按你的板子改 GPIO

async def main():
    print('blink @ GPIO2 started')
    while not uvm.should_stop():
        led.value(not led.value())
        await uvm.sleep_ms(500)
    led.value(0)
    print('blink stopped')
"""

SYNC_TEMPLATE = """#type:sync
# 同步脚本：在独立线程里运行，跑完即止
import uvm

print('hello from sync program')
for i in range(10):
    uvm.sleep_ms(500)
    print('tick', i)
print('done')
"""

_EXT_TYPES = {
    'html': 'text/html; charset=utf-8',
    'css': 'text/css; charset=utf-8',
    'js': 'application/javascript; charset=utf-8',
    'json': 'application/json',
    'txt': 'text/plain; charset=utf-8',
    'png': 'image/png',
    'ico': 'image/x-icon',
    'svg': 'image/svg+xml',
    'map': 'application/json',
}

_sessions = {}          # token -> 过期时间戳(ms)
SESSION_TTL_MS = 7 * 24 * 3600 * 1000   # 7 天
_api = None


def _now_ms():
    """当前时间戳(ms)，兼容 MicroPython(ticks_ms) 与 CPython(time.time)。"""
    if hasattr(time, 'ticks_ms'):
        return time.ticks_ms()
    return int(time.time() * 1000)


async def _sleep_ms(ms):
    """兼容 MicroPython(uasyncio.sleep_ms) 与 CPython(asyncio.sleep)。"""
    if hasattr(asyncio, 'sleep_ms'):
        await asyncio.sleep_ms(ms)
    else:
        await asyncio.sleep(ms / 1000.0)


def _load_cfg():
    return config.load()


def _session_valid(token):
    if not token:
        return False
    exp = _sessions.get(token)
    if exp is None:
        return False
    if _now_ms() > exp:
        _sessions.pop(token, None)
        return False
    return True


def _authorized(request):
    cfg = _load_cfg()
    auth = cfg.get('auth', {}) or {}
    if not auth.get('enabled'):
        return True
    if auth.get('password') == '':
        return True
    # 同时支持 Cookie 与 X-Auth-Token 请求头（前端用请求头发 token）
    token = request.cookies.get('token')
    if _session_valid(token):
        return True
    token = request.headers.get('X-Auth-Token', '')
    if _session_valid(token):
        return True
    return False


def _ws_authorized(request):
    cfg = _load_cfg()
    auth = cfg.get('auth', {}) or {}
    if not auth.get('enabled'):
        return True
    if auth.get('password') == '':
        return True
    token = ''
    qs = request.query_string or b''
    if isinstance(qs, bytes):
        qs = qs.decode('utf-8', 'replace')
    for part in qs.split('&'):
        if part.startswith('token='):
            token = part[6:]
            break
    return _session_valid(token)


def _live_net():
    info = {'ap_ip': None, 'sta_ip': None, 'sta_connected': False}
    try:
        import network
        ap = network.WLAN(network.AP_IF)
        sta = network.WLAN(network.STA_IF)
        try:
            if ap.active():
                info['ap_ip'] = ap.ifconfig()[0]
        except Exception:
            pass
        try:
            if sta.active() and sta.isconnected():
                info['sta_ip'] = sta.ifconfig()[0]
                info['sta_connected'] = True
        except Exception:
            pass
    except Exception:
        pass
    return info


def _sys_info():
    mem_free = 0
    try:
        gc.collect()
        mem_free = gc.mem_free()
    except Exception:
        pass
    fs = {'total': 0, 'free': 0}
    try:
        st = os.statvfs('/')
        fs['total'] = st[0] * st[1]
        fs['free'] = st[0] * st[3]
    except Exception:
        pass
    net = _live_net()
    return {
        'mem_free': mem_free,
        'filesystem': fs,
        'net': net,
        'version': sys.version,
    }


def create_app(manager, hub):
    global _api
    app = Microdot()

    # 鉴权打包器
    def authed(fn):
        async def wrapper(request, *args, **kwargs):
            if not _authorized(request):
                return _json_error('未登录或会话已过期', 401)
            return await fn(request, *args, **kwargs)
        return wrapper

    def _json_error(msg, status=400):
        return {'error': msg}, status

    def _ok(msg):
        return {'ok': True, 'message': msg}

    # ---------- 鉴权 ----------

    @app.post('/api/login')
    async def login(request):
        cfg = _load_cfg()
        auth = cfg.get('auth', {}) or {}
        if not auth.get('enabled'):
            return {'ok': True, 'token': ''}
        body = request.json or {}
        if str(body.get('password', '')) == str(auth.get('password', '')):
            token = _new_token()
            _sessions[token] = _now_ms() + SESSION_TTL_MS
            resp = Response(
                json.dumps({'ok': True, 'token': token}),
                status_code=200,
                headers={'Content-Type': 'application/json',
                         'Set-Cookie': ['token=%s; Path=/' % token]})
            return resp
        return _json_error('密码错误', 403)

    @app.post('/api/logout')
    @authed
    async def logout(request):
        token = request.cookies.get('token')
        if token in _sessions:
            del _sessions[token]
        token = request.headers.get('X-Auth-Token', '')
        if token in _sessions:
            del _sessions[token]
        resp = Response(json.dumps({'ok': True}),
                        status_code=200,
                        headers={'Content-Type': 'application/json',
                                 'Set-Cookie': ['token=; Max-Age=0; Path=/']})
        return resp

    # ---------- 程序管理 ----------

    @app.get('/api/programs')
    @authed
    async def api_list(request):
        return {'programs': manager.status_snapshot()}

    @app.post('/api/programs')
    @authed
    async def api_create(request):
        body = request.json or {}
        name = str(body.get('name', '')).strip()
        code = body.get('code')
        templ = body.get('template')
        if code is None or code == '':
            code = ASYNC_TEMPLATE if templ == 'async' else SYNC_TEMPLATE
        try:
            nm = manager.create_program(name, code)
            return {'ok': True, 'name': nm}
        except RuntimeError as e:
            return _json_error(str(e))

    @app.get('/api/programs/<name>')
    @authed
    async def api_get(request, name):
        try:
            code = manager.read_code(name)
            p = manager.get_program(name)
            return {'name': name, 'type': p.type, 'code': code}
        except (OSError, RuntimeError) as e:
            return _json_error('读取失败：%s' % e, 404)

    @app.put('/api/programs/<name>')
    @authed
    async def api_save(request, name):
        body = request.json or {}
        code = body.get('code')
        if code is None:
            return _json_error('缺少 code 字段')
        try:
            p = manager.save_code(name, code)
            return {'ok': True, 'type': p.type}
        except RuntimeError as e:
            return _json_error(str(e))

    @app.delete('/api/programs/<name>')
    @authed
    async def api_delete(request, name):
        try:
            manager.delete_program(name)
            return _ok('已删除 %s' % name)
        except RuntimeError as e:
            return _json_error(str(e))

    @app.post('/api/programs/<name>/rename')
    @authed
    async def api_rename(request, name):
        body = request.json or {}
        new_name = str(body.get('name', '')).strip()
        try:
            nm = manager.rename_program(name, new_name)
            return {'ok': True, 'name': nm}
        except RuntimeError as e:
            return _json_error(str(e))

    @app.post('/api/programs/<name>/start')
    @authed
    async def api_start(request, name):
        try:
            p = manager.start(name)
            return {'ok': True, 'message': '已启动 %s' % name, 'type': p.type}
        except (RuntimeError, OSError) as e:
            return _json_error(str(e))

    @app.post('/api/programs/<name>/stop')
    @authed
    async def api_stop(request, name):
        try:
            manager.stop(name)
            return {'ok': True, 'message': '已请求停止 %s' % name}
        except (RuntimeError, OSError) as e:
            return _json_error(str(e))

    @app.post('/api/programs/<name>/restart')
    @authed
    async def api_restart(request, name):
        body = request.json or {}
        code = body.get('code')
        try:
            p = await manager.restart(name, code)
            return {'ok': True, 'message': '已重启 %s' % name, 'type': p.type}
        except (RuntimeError, OSError) as e:
            return _json_error(str(e))

    # ---------- 状态 / 配置 ----------

    @app.get('/api/status')
    @authed
    async def api_status(request):
        return {'programs': manager.status_snapshot(), 'sys': _sys_info()}

    @app.get('/api/config')
    @authed
    async def api_get_config(request):
        cfg = _load_cfg()
        return {
            'wifi': {'ssid': cfg['wifi'].get('ssid', '')},
            'ap': {'enabled': bool(cfg['ap'].get('enabled', True)),
                   'ssid': cfg['ap'].get('ssid', '')},
            'auth': {'enabled': bool(cfg['auth'].get('enabled', False))},
            'autostart': list(cfg.get('autostart', [])),
        }

    @app.post('/api/config')
    @authed
    async def api_set_config(request):
        cfg = _load_cfg()
        body = request.json or {}
        if 'wifi' in body and isinstance(body['wifi'], dict):
            w = body['wifi']
            if isinstance(w.get('ssid'), str):
                cfg['wifi']['ssid'] = w['ssid']
            if isinstance(w.get('password'), str) and w['password'] != '':
                cfg['wifi']['password'] = w['password']
        if 'ap' in body and isinstance(body['ap'], dict):
            a = body['ap']
            if 'enabled' in a:
                cfg['ap']['enabled'] = bool(a['enabled'])
            if isinstance(a.get('ssid'), str) and a['ssid'] != '':
                cfg['ap']['ssid'] = a['ssid']
            if isinstance(a.get('password'), str) and a['password'] != '':
                cfg['ap']['password'] = a['password']
        if 'auth' in body and isinstance(body['auth'], dict):
            au = body['auth']
            if 'enabled' in au:
                cfg['auth']['enabled'] = bool(au['enabled'])
            if isinstance(au.get('password'), str) and au['password'] != '':
                cfg['auth']['password'] = au['password']
        if 'autostart' in body and isinstance(body['autostart'], list):
            cfg['autostart'] = [s for s in body['autostart']
                                if isinstance(s, str) and s in
                                [n['name'] for n in manager.status_snapshot()]]
        config.save(cfg)
        try:
            import net
            net.reconfigure(hub.console)
        except Exception:
            pass
        return {'ok': True, 'message': '配置已保存，网络正在应用'}

    @app.post('/api/reboot')
    @authed
    async def api_reboot(request):
        async def _do():
            await _sleep_ms(200)
            try:
                import machine
                machine.reset()
            except Exception:
                pass
        asyncio.create_task(_do())
        return _ok('正在重启...')

    # ---------- WiFi 扫描 ----------

    @app.get('/api/scan')
    @authed
    async def api_scan(request):
        try:
            import network
        except Exception:
            return _json_error('当前环境不支持网络扫描')
        try:
            sta = network.WLAN(network.STA_IF)
            was_active = bool(sta.active())
            if not was_active:
                sta.active(True)
            try:
                results = sta.scan()
            finally:
                if not was_active and sta.active():
                    sta.active(False)
        except Exception as e:
            return _json_error('扫描失败：%s' % str(e))
        out = []
        for n in results:
            try:
                ssid = n[0].decode('utf-8', 'replace') if isinstance(n[0], bytes) else str(n[0])
            except Exception:
                ssid = ''
            if not ssid:
                continue
            rssi = n[3] if len(n) > 3 else 0
            auth = n[4] if len(n) > 4 else 0
            out.append({'ssid': ssid, 'rssi': rssi, 'auth': auth})
        return {'networks': out}

    # ---------- WebSocket 实时控制台 ----------

    @app.route('/ws')
    async def ws_route(request):
        # 延迟 import：microdot.websocket 会引入 hashlib/binascii，
        # C3 内存紧张，等真有 WebSocket 连接再加载
        from microdot.websocket import with_websocket
        return await with_websocket(_ws_impl)(request)

    async def _ws_impl(request, ws):
        if not _ws_authorized(request):
            try:
                await ws.close()
            except Exception:
                pass
            return
        client = hub.register(ws)
        receiver = asyncio.create_task(hub.receiver(ws, client))
        sender = asyncio.create_task(hub.sender(ws, client))
        client['sender'] = sender
        client['receiver'] = receiver
        try:
            await asyncio.gather(receiver, sender, return_exceptions=True)
        finally:
            hub.unregister(client)
            for t in (receiver, sender):
                try:
                    t.cancel()
                except Exception:
                    pass

    # ---------- 静态文件 ----------

    @app.get('/')
    async def index(request):
        return _serve(WWW_DIR + '/index.html', 'text/html; charset=utf-8', 0)

    @app.get('/<path:path>')
    async def static_catch(request, path):
        safe = path.replace('\\', '/')
        if '..' in safe.split('/'):
            return _json_error('bad path', 404)
        ext = safe.rsplit('.', 1)[-1].lower() if '.' in safe else ''
        ct = _EXT_TYPES.get(ext, 'application/octet-stream')
        if safe.startswith('cm/'):
            return _serve(CM_DIR + '/' + safe[3:], ct, 3600)
        return _serve(WWW_DIR + '/' + safe, ct, 0)

    _api = app
    return app


def _serve(full_path, content_type, max_age):
    try:
        return Response.send_file(full_path, content_type=content_type,
                                  max_age=max_age)
    except OSError:
        return {'error': 'not found'}, 404


def _new_token():
    try:
        import os as _os
        return _os.urandom(9).hex()
    except Exception:
        import time as _time
        return '%08x%08x' % (_time.ticks_ms(), _time.ticks_us())


class Hub:
    """把控制台日志广播给所有已连接的 WebSocket 客户端。"""

    MAX_QUEUE = config.hub_max_queue()

    def __init__(self, console):
        self.console = console
        self.clients = []
        console.on_line(self._on_line)

    def _on_line(self, line):
        payload = json.dumps({'type': 'console', 'line': line})
        for c in list(self.clients):
            q = c['queue']
            q.append(payload)
            if len(q) > self.MAX_QUEUE:
                del q[: len(q) - self.MAX_QUEUE]

    def register(self, ws):
        client = {'ws': ws, 'queue': [], 'closed': False,
                  'sender': None, 'receiver': None}
        for line in self.console.history():
            client['queue'].append(
                json.dumps({'type': 'console', 'line': line}))
        self.clients.append(client)
        return client

    def unregister(self, client):
        try:
            client['closed'] = True
            if client in self.clients:
                self.clients.remove(client)
        except Exception:
            pass

    def _handle(self, ws, client, msg):
        if not isinstance(msg, str):
            msg = msg.decode('utf-8', 'replace')
        try:
            data = json.loads(msg)
        except Exception:
            data = None
        if isinstance(data, dict):
            t = data.get('type')
            if t == 'clear':
                self.console.clear()
                q = client['queue']
                q.append(json.dumps({'type': 'console', 'action': 'cleared'}))
            elif t == 'ping':
                q = client['queue']
                q.append(json.dumps({'type': 'pong'}))

    async def receiver(self, ws, client):
        try:
            while True:
                msg = await ws.receive()
                if msg is None:
                    break
                self._handle(ws, client, msg)
        except Exception:
            pass
        finally:
            client['closed'] = True
            try:
                await ws.close()
            except Exception:
                pass
            sender = client['sender']
            if sender is not None:
                try:
                    sender.cancel()
                except Exception:
                    pass

    async def sender(self, ws, client):
        try:
            while not client['closed']:
                while client['queue'] and not client['closed']:
                    payload = client['queue'].pop(0)
                    try:
                        await ws.send(payload)
                    except Exception:
                        client['closed'] = True
                        break
                if client['closed']:
                    break
                await asyncio.sleep(0.05)
        except Exception:
            pass
        finally:
            client['closed'] = True
            receiver = client['receiver']
            if receiver is not None:
                try:
                    receiver.cancel()
                except Exception:
                    pass