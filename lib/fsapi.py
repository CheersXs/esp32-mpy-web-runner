"""文件系统管理 API：/api/fs/* 路由（文件管理器 + 远程更新）。

按 C3 内存纪律（见 docs/C3_PORTING_GUIDE.md）：本模块 + fsmgr 属"小模块"，
由 web.create_app() 在 GC 堆稳定后延迟注册（C3 中 create_app 在 c3_app.run
阶段才被调用），**不参与** main.py 的固定导入序列 web→runner→config→console
（顺序不可乱，插入任何模块都会增大 web 最大模块的编译峰值、挤占 split-heap
导入窗口 → wifi 数据通路饿死）。
"""

import fsmgr


def register(app, config, authed, json_error, ok, sys_info):
    """把 /api/fs/* 路由注册到 app。在 GC 堆稳定后调用（web.create_app 末尾）。"""

    def _fs_path(request):
        path = ''
        if request.args:
            path = request.args.get('path', '')
        return fsmgr.normalize(path)

    @app.get('/api/fs/list')
    @authed
    async def api_fs_list(request):
        p = _fs_path(request)
        if p is None:
            return json_error('bad path')
        try:
            data = fsmgr.list_dir(p)
        except OSError:
            return json_error('Not found', 404)
        data['free'] = sys_info()['filesystem']['free']
        data['dangerous'] = fsmgr.is_dangerous(p)
        return data

    @app.get('/api/fs/read')
    @authed
    async def api_fs_read(request):
        p = _fs_path(request)
        if p is None:
            return json_error('bad path')
        sz = fsmgr.size(p)
        if sz < 0:
            return json_error('Not found', 404)
        if fsmgr.is_dir(p):
            return json_error('Is a directory', 400)
        limit = config.fs_edit_max()
        if sz > limit:
            return json_error(
                'File too large to edit in browser (%d B > %d B limit). '
                'Use download + re-upload instead.' % (sz, limit), 413)
        try:
            offset = 0
            want = limit
            if request.args:
                offset = int(request.args.get('offset', '0') or '0')
                if request.args.get('limit'):
                    want = int(request.args.get('limit'))
            if offset < 0 or offset > sz or want <= 0 or want > limit:
                return json_error('bad range', 400)
            text, end = fsmgr.read_range(p, offset, want)
        except ValueError as e:
            return json_error(str(e))
        except Exception as e:
            return json_error('Failed to read: %s' % e, 500)
        done = end >= sz
        base = {'path': p, 'size': sz, 'text': text,
                'offset': end, 'limit': want, 'done': done}
        if offset == 0:
            base['name'] = p.rsplit('/', 1)[-1]
            base['dangerous'] = fsmgr.is_dangerous(p)
        return base

    @app.get('/api/fs/file')
    @authed
    async def api_fs_download(request):
        from microdot.microdot import Response
        p = _fs_path(request)
        if p is None:
            return json_error('bad path')
        if fsmgr.is_dir(p):
            return json_error('Is a directory', 400)
        real = fsmgr._real(p)
        try:
            resp = Response.send_file(real, content_type='application/octet-stream',
                                      max_age=0)
        except OSError:
            return json_error('Not found', 404)
        resp.headers['Content-Disposition'] = \
            'attachment; filename="%s"' % p.rsplit('/', 1)[-1]
        return resp

    @app.put('/api/fs/file')
    @authed
    async def api_fs_upload(request):
        p = _fs_path(request)
        if p is None:
            return json_error('bad path')
        if fsmgr.is_dir(p):
            return json_error('Is a directory', 400)
        append = bool(request.args and request.args.get('append')
                      in ('1', 'true', 'True'))
        final = bool(request.args and request.args.get('final')
                     in ('1', 'true', 'True'))
        # 显式带 append 参数即分片保存（首片 append=0 也走分片路径，开 .tmp
        # 覆盖；否则首片走 write_bytes 立即提交、后续片 append 到 .tmp，
        # 最后提交时首片会丢失）。
        chunked = bool(request.args and 'append' in request.args)
        try:
            if chunked:
                if not request.body:
                    return json_error('chunked save needs a body')
                fsmgr.write_append(p, request.body, append=append, final=final)
            elif request.body:
                fsmgr.write_bytes(p, request.body)
            else:
                await fsmgr.write_stream(p, request.stream)
        except ValueError as e:
            return json_error(str(e))
        except OSError as e:
            return json_error('Write failed: %s' % e)
        return {'ok': True, 'message': 'Saved %s' % p, 'path': p,
                'dangerous': fsmgr.is_dangerous(p)}

    @app.post('/api/fs/mkdir')
    @authed
    async def api_fs_mkdir(request):
        p = _fs_path(request)
        if p is None or p == '/':
            return json_error('bad path')
        if fsmgr.exists(p):
            return json_error('Already exists')
        try:
            fsmgr.mkdir(p)
        except OSError as e:
            return json_error('mkdir failed: %s' % e)
        return ok('Created directory %s' % p)

    @app.post('/api/fs/rename')
    @authed
    async def api_fs_rename(request):
        try:
            body = request.json
        except Exception:
            return json_error('Request body is not valid JSON')
        if body is None or not isinstance(body, dict):
            return json_error('Request body must be a JSON object')
        src = fsmgr.normalize(str(body.get('from', '')))
        dst = fsmgr.normalize(str(body.get('to', '')))
        if src is None or dst is None:
            return json_error('bad path')
        if fsmgr.is_dangerous(src) or fsmgr.is_dangerous(dst):
            if not body.get('force'):
                return json_error('This is a system file, pass force=1 to confirm', 400)
        try:
            fsmgr.rename(src, dst)
        except (ValueError, OSError) as e:
            return json_error(str(e))
        return ok('Renamed %s -> %s' % (src, dst))

    @app.post('/api/fs/delete')
    @authed
    async def api_fs_delete(request):
        p = _fs_path(request)
        if p is None:
            return json_error('bad path')
        if p == '/':
            return json_error('Cannot delete root')
        if fsmgr.is_dangerous(p) and not (request.args and request.args.get('force')):
            return json_error('This is a system file, pass force=1 to confirm', 400)
        recursive = bool(request.args and request.args.get('recursive') in ('1', 'true', 'True'))
        try:
            fsmgr.delete(p, recursive=recursive)
        except (ValueError, OSError) as e:
            return json_error(str(e))
        return ok('Deleted %s' % p)