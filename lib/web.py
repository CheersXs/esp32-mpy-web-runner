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

# 允许较大的上传请求体（默认 16KB 会拒绝大文件）。超过 max_body_length 的
# 请求体留在 request.stream 里流式写盘，内存安全，不一次性读入。
Request.max_content_length = 1024 * 1024

WWW_DIR = '/www'
CM_DIR = WWW_DIR + '/cm'

ASYNC_TEMPLATE = """#type:async
# Board switchable async program (can be stopped from the web page at any time)
import uvm
import machine

led = machine.Pin(2, machine.Pin.OUT)   # change the GPIO to match your board

async def main():
    print('blink @ GPIO2 started')
    while not uvm.should_stop():
        led.value(not led.value())
        await uvm.sleep_ms(500)
    led.value(0)
    print('blink stopped')
"""

SYNC_TEMPLATE = """#type:sync
# Sync script: runs in a dedicated thread, ends when done
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
        'app_version': config.VERSION,
        'board': config.board(),
    }


# ---------- C3 并发保护 ----------
# C3 单核 + 小 lwIP pbuf：同时处理过多请求（尤其大响应传输）会耗尽缓冲，
# 表现为其余请求全部挂起（CM 分片传输时实测）。限制同时处理的请求数，
# 超限的直接关闭连接（浏览器 fetch 报网络错误，前端已静默跳过/降级）。
# S3 多核不限。PC/测试环境 is_c3()=False，同样不限。
_MAX_CONCURRENT = 3 if config.is_c3() else 0
_active_requests = 0
_guard_installed = False


def _install_concurrency_guard():
    global _guard_installed
    if _guard_installed:
        return
    _guard_installed = True
    import microdot.microdot as _mdot
    _orig_handle = _mdot.Microdot.handle_request

    async def _guarded(self, reader, writer):
        global _active_requests
        if _MAX_CONCURRENT and _active_requests >= _MAX_CONCURRENT:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            return
        _active_requests += 1
        try:
            await _orig_handle(self, reader, writer)
        finally:
            _active_requests -= 1

    _mdot.Microdot.handle_request = _guarded


def create_app(manager, hub):
    global _api
    _install_concurrency_guard()
    app = Microdot()

    # 鉴权打包器
    def authed(fn):
        async def wrapper(request, *args, **kwargs):
            if not _authorized(request):
                return _json_error('Not logged in or session expired', 401)
            return await fn(request, *args, **kwargs)
        return wrapper

    def _json_error(msg, status=400):
        return {'error': msg}, status

    def _json_body(request):
        try:
            body = request.json
        except Exception:
            return None, _json_error('Request body is not valid JSON')
        if body is None:
            return {}, None
        if not isinstance(body, dict):
            return None, _json_error('Request body must be a JSON object')
        return body, None

    def _ok(msg):
        return {'ok': True, 'message': msg}

    # ---------- 鉴权 ----------

    @app.post('/api/login')
    async def login(request):
        cfg = _load_cfg()
        auth = cfg.get('auth', {}) or {}
        if not auth.get('enabled'):
            return {'ok': True, 'token': ''}
        body, jerr = _json_body(request)
        if jerr is not None:
            return jerr
        if str(body.get('password', '')) == str(auth.get('password', '')):
            token = _new_token()
            _sessions[token] = _now_ms() + SESSION_TTL_MS
            resp = Response(
                json.dumps({'ok': True, 'token': token}),
                status_code=200,
                headers={'Content-Type': 'application/json',
                         'Set-Cookie': ['token=%s; Path=/' % token]})
            return resp
        return _json_error('Wrong password', 403)

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
        body, jerr = _json_body(request)
        if jerr is not None:
            return jerr
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
            return _json_error('Failed to read: %s' % e, 404)

    @app.put('/api/programs/<name>')
    @authed
    async def api_save(request, name):
        body, jerr = _json_body(request)
        if jerr is not None:
            return jerr
        code = body.get('code')
        if code is None:
            return _json_error('Missing "code" field')
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
            return _ok('Deleted %s' % name)
        except RuntimeError as e:
            return _json_error(str(e))

    @app.post('/api/programs/<name>/rename')
    @authed
    async def api_rename(request, name):
        body, jerr = _json_body(request)
        if jerr is not None:
            return jerr
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
            return {'ok': True, 'message': 'Started %s' % name, 'type': p.type}
        except (RuntimeError, OSError) as e:
            return _json_error(str(e))

    @app.post('/api/programs/<name>/stop')
    @authed
    async def api_stop(request, name):
        try:
            manager.stop(name)
            return {'ok': True, 'message': 'Stop requested for %s' % name}
        except (RuntimeError, OSError) as e:
            return _json_error(str(e))

    @app.post('/api/programs/<name>/restart')
    @authed
    async def api_restart(request, name):
        body, jerr = _json_body(request)
        if jerr is not None:
            return jerr
        code = body.get('code')
        try:
            p = await manager.restart(name, code)
            return {'ok': True, 'message': 'Restarted %s' % name, 'type': p.type}
        except (RuntimeError, OSError) as e:
            return _json_error(str(e))

    # ---------- 文件系统管理（文件管理器 / 远程更新） ----------
    # fsapi/fsmgr 属"小模块"，按 C3 内存纪律（docs/C3_PORTING_GUIDE.md）在
    # GC 堆稳定后才延迟加载：保持 web（最大模块）固定导入序列不变，避免编译
    # 峰值顶破 split-heap 阈值 → wifi 数据通路饿死。
    # C3 实测启动后 GC free 仅剩 ~7KB（v2.2.0 新增 fsapi/fsmgr 后），81KB 内联
    # 页都传不完整。fsapi/fsmgr（~10KB）改为"首次 /api/fs/* 请求才 import"：
    # 页面加载这段大传输发生在 fsapi/fsmgr 未加载、内存最充裕的时段；首次进入
    # 文件管理器时才加载，随后常驻。S3 内存充裕，行为不变（首次请求同样延迟）。
    _fs_loaded = [False]

    @app.route('/api/fs/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
    async def _fs_proxy(request, path):
        if not _fs_loaded[0]:
            import fsapi
            fsapi.register(app, config, authed, _json_error, _ok, _sys_info)
            _fs_loaded[0] = True
        # fsapi 精确路由是懒加载时才 append 到 url_map 末尾（位于静态兜底
        # /<path:path> 之后），故必须倒序命中，否则会被静态路由抢走。
        # 代理常驻：/api/fs/* 一律经此分发，行为与直接注册一致。
        method = request.method.upper()
        if method == 'HEAD':
            method = 'GET'
        for route_methods, pattern, route_handler, _, _ in reversed(app.url_map):
            if route_handler is _fs_proxy:
                continue
            if method in route_methods:
                args = pattern.match(request.path)
                if args is not None:
                    return await route_handler(request, **args)
        return _json_error('Not found', 404)

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
        body, jerr = _json_body(request)
        if jerr is not None:
            return jerr
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
        return {'ok': True, 'message': 'Config saved, applying network changes'}

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
        return _ok('Rebooting...')

    # ---------- WiFi 扫描 ----------

    @app.get('/api/scan')
    @authed
    async def api_scan(request):
        try:
            import network
        except Exception:
            return _json_error('Network scanning not supported in this environment')
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
            return _json_error('Scan failed: %s' % str(e))
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
            rel = safe[3:]
            # 预压缩版本优先：C3 弱射频扛不住 ~193KB 单次传输（实测打开
            # 编辑器拉 cm-bundle 即压垮网络栈），gzip 后 ~65KB。浏览器按
            # Content-Encoding:gzip 自动解压。板上只传 .gz（无未压缩包），
            # 若 .gz 也失败浏览器只会 404 → textarea 兜底，页面不崩。
            gz = CM_DIR + '/' + rel + '.gz'
            try:
                os.stat(gz)
            except OSError:
                gz = None
            if gz:
                try:
                    return Response.send_file(gz, content_type=ct, max_age=3600,
                                              compressed=True)
                except OSError:
                    pass
            return _serve(CM_DIR + '/' + rel, ct, 3600)
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