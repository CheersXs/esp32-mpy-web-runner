#!/usr/bin/env python3
"""PC 端冒烟测试：不依赖板子，用 CPython + microdot 测试客户端把
REST API 和 asyncio/线程调度逻辑跑一遍。

用法:  python tools/smoke_test.py
（可选环境变量 RUN_WITH_LINE=1 在最后再跑一遍单元冒烟）
"""
import json
import os
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))

import asyncio  # noqa: E402

import config  # noqa: E402
import console  # noqa: E402
import fsmgr  # noqa: E402
import runner  # noqa: E402
import web  # noqa: E402

TMP = tempfile.mkdtemp(prefix='esp32wr_')
config.CONFIG_PATH = os.path.join(TMP, 'config.json')
runner.PROGRAMS_DIR = os.path.join(TMP, 'programs')
web.WWW_DIR = os.path.join(ROOT, 'www')
web.CM_DIR = os.path.join(web.WWW_DIR, 'cm')
fsmgr.FS_ROOT = os.path.join(TMP, 'fs')


def make_app():
    con = console.Console(max_lines=100)
    con.attach()

    def sub(line):
        pass

    con.on_line(sub)
    manager = runner.Manager(con)
    hub = web.Hub(con)
    app = web.create_app(manager, hub)
    return app, manager, con, lines_of(con), hub


def lines_of(con):
    return con.buffer


SYNC_CODE = ("#type:sync\n"
             "import uvm\n"
             "print('hello-start')\n"
             "for i in range(3):\n"
             "    uvm.sleep_ms(100)\n"
             "    print('tick', i)\n"
             "print('hello-done')\n")

ASYNC_CODE = ("#type:async\n"
              "import uvm\n"
              "async def main():\n"
              "    print('async-start')\n"
              "    while not uvm.should_stop():\n"
              "        await uvm.sleep_ms(60)\n"
              "        print('beat')\n"
              "    print('async-stop')\n")

BAD_CODE = "def ( :\n"


async def main():
    app, manager, con, lines, hub = make_app()
    from microdot.test_client import TestClient
    cli = TestClient(app)
    passed = 0
    failed = 0

    def check(name, cond, extra=''):
        nonlocal passed, failed
        if cond:
            passed += 1
            print('  PASS  %s' % name)
        else:
            failed += 1
            print('  FAIL  %s  %s' % (name, extra))

    # 1. 静态文件
    r = await cli.get('/')
    ct0 = r.headers.get('Content-Type')
    check('GET / 200', r.status_code == 200,
          'code=%s ct=%s' % (getattr(r, 'status_code', '?'), ct0))
    r = await cli.get('/app.js')
    ctt = r.headers.get('Content-Type')
    check('GET /app.js', r.status_code == 200 and ctt and 'javascript' in ctt,
          'code=%s ct=%s len=%s' % (getattr(r, 'status_code', '?'), ctt,
                                    len(r.text or '')))
    r = await cli.get('/cm/codemirror.min.js')
    check('GET /cm/codemirror.min.js', r.status_code == 200 and len((r.text or '')) > 1000,
          'code=%s len=%s' % (getattr(r, 'status_code', '?'), len(r.text or '')))

    # 2. 新建程序
    r = await cli.post('/api/programs', body={'name': 'hello', 'code': SYNC_CODE})
    check('POST /api/programs(hello)', r.status_code == 200, (r.text or '')[:100])
    r = await cli.post('/api/programs', body={'name': 'blink', 'code': ASYNC_CODE})
    check('POST /api/programs(blink)', r.status_code == 200)
    r = await cli.post('/api/programs', body={'name': 'bad', 'code': BAD_CODE})
    check('POST 语法错误被拒', r.status_code == 400)
    r = await cli.post('/api/programs', body={'name': 'bad name!', 'code': 'x=1'})
    check('非法名字被拒', r.status_code == 400)
    r = await cli.post('/api/programs', body={'name': '中文名', 'code': 'x=1'})
    check('中文名被拒', r.status_code == 400, (r.text or '')[:100])

    # 3. 列表 / 读取
    r = await cli.get('/api/programs')
    names = [p['name'] for p in r.json['programs']]
    check('列表含 hello/blink', 'hello' in names and 'blink' in names, str(names))
    r = await cli.get('/api/programs/hello')
    check('读取代码', r.json.get('code') == SYNC_CODE)

    # 4. 启动同步程序（线程）→ 等待结束
    r = await cli.post('/api/programs/hello/start', body={})
    check('启动 hello(start)', r.status_code == 200, (r.text or '')[:120])
    for _ in range(60):
        st = manager.get_program('hello')
        if st.status != 'running':
            break
        await asyncio.sleep(0.05)
    check('hello 线程跑完变 stopped', st.status == 'stopped', 'status=' + st.status)
    check('hello 控制台有输出', any('tick' in l for l in lines))

    # 5. 启动异步程序 → 停止
    r = await cli.post('/api/programs/blink/start', body={})
    check('启动 blink(start)', r.status_code == 200)
    await asyncio.sleep(0.3)
    check('blink 正在运行', manager.is_running('blink'))
    r = await cli.post('/api/programs/blink/stop', body={})
    check('停止 blink(stop)', r.status_code == 200)
    for _ in range(60):
        st = manager.get_program('blink')
        if st.status != 'running':
            break
        await asyncio.sleep(0.05)
    check('blink 已停止', st.status == 'stopped', 'status=' + st.status)

    # 5b. 保存并重启（运行中程序）：先停止 → 保存 → 启动
    r = await cli.post('/api/programs/blink/start', body={})
    check('重启前启动 blink', r.status_code == 200)
    await asyncio.sleep(0.2)
    check('blink 运行中', manager.is_running('blink'))
    new_code = ASYNC_CODE + '# edited\n'
    r = await cli.post('/api/programs/blink/restart', body={'code': new_code})
    check('保存并重启 blink', r.status_code == 200, (r.text or '')[:120])
    for _ in range(60):
        st = manager.get_program('blink')
        if st.status == 'running':
            break
        await asyncio.sleep(0.05)
    check('blink 重启后运行中', st.status == 'running', 'status=' + st.status)
    r = await cli.get('/api/programs/blink')
    check('重启后代码已保存', r.json.get('code') == new_code)
    r = await cli.post('/api/programs/blink/stop', body={})
    check('停止 blink', r.status_code == 200)
    for _ in range(60):
        st = manager.get_program('blink')
        if st.status != 'running':
            break
        await asyncio.sleep(0.05)
    check('blink 已停止', st.status == 'stopped', 'status=' + st.status)

    # 6. PUT 保存 / 重命名 / 删除
    r = await cli.put('/api/programs/hello', body={'code': SYNC_CODE + '# edited\n'})
    check('PUT 保存', r.status_code == 200)
    r = await cli.post('/api/programs/hello/rename', body={'name': 'hello2'})
    check('rename -> hello2', r.status_code == 200 and r.json.get('name') == 'hello2')
    r = await cli.delete('/api/programs/hello2')
    check('delete hello2', r.status_code == 200)
    r = await cli.get('/api/programs/hello2')
    check('删除后读取 404', r.status_code == 404)

    # 7. 状态 / 配置
    r = await cli.get('/api/status')
    check('GET /api/status', r.status_code == 200 and 'programs' in r.json)
    r = await cli.post('/api/config', body={
        'wifi': {'ssid': 'test-ssid', 'password': 'pw123'},
        'autostart': ['blink'],
    })
    check('POST /api/config', r.status_code == 200)
    r = await cli.get('/api/config')
    check('config 已保存', r.json['wifi']['ssid'] == 'test-ssid')
    check('autostart 已保存', r.json['autostart'] == ['blink'])

    # 8. 登录（关闭密码保护时直接通过）
    r = await cli.post('/api/login', body={'password': 'x'})
    check('login(无保护)', r.status_code == 200)

    # 8b. 开启密码保护后验证鉴权
    config.save({'wifi': {'ssid': '', 'password': ''},
                 'ap': {'ssid': 'T', 'password': ''},
                 'auth': {'enabled': True, 'password': 'secret'},
                 'autostart': []})
    r = await cli.get('/api/programs')
    check('开启保护后未登录被拒', r.status_code == 401)
    r = await cli.get('/')
    check('静态首页可访问(显示登录UI)', r.status_code == 200)
    r = await cli.post('/api/login', body={'password': 'wrong'})
    check('错误密码被拒', r.status_code == 403)
    r = await cli.post('/api/login', body={'password': 'secret'})
    check('正确密码登录', r.status_code == 200 and r.json.get('token'))
    token = r.json['token']
    r = await cli.get('/api/programs', headers={'Cookie': 'token=' + token})
    check('带 token 可访问', r.status_code == 200)
    config.save({'wifi': {'ssid': '', 'password': ''},
                 'ap': {'ssid': 'T', 'password': ''},
                 'auth': {'enabled': False, 'password': ''},
                 'autostart': []})
    r = await cli.get('/api/programs')
    check('关闭保护后恢复', r.status_code == 200)

    # 9. Hub 广播不抛异常
    try:
        con._push('broadcast-line')
        hub._on_line('aaaa')
        check('hub 广播', True)
    except Exception as e:
        check('hub 广播', False, repr(e))

    # 10. 非法操作
    r = await cli.post('/api/programs/nonexist/start', body={})
    check('启动不存在程序报错', r.status_code == 400)
    r = await cli.post('/api/programs', body=b'',
                       headers={'Content-Type': 'application/json'})
    check('空请求体返回 400 而非 500', r.status_code == 400, (r.text or '')[:100])
    r = await cli.post('/api/programs', body='not-json',
                       headers={'Content-Type': 'application/json'})
    check('畸形请求体返回 400 而非 500', r.status_code == 400, (r.text or '')[:100])

    # 11. #type 类型识别（_resolve_type）
    check('自动识别 async (含 async def main)',
          runner.Manager._resolve_type('x = 1\nasync def main():\n    pass\n') == 'async')
    check('自动识别 sync (无 async def main)',
          runner.Manager._resolve_type('x = 1\nprint(x)\n') == 'sync')
    check('#type:sync 强制覆盖 async def main',
          runner.Manager._resolve_type('#type:sync\nasync def main():\n    pass\n') == 'sync')
    check('#type:async 强制',
          runner.Manager._resolve_type('#type:async\nx = 1\n') == 'async')

    # 11b. _safe_name（S3 固件缺失 str.isalnum，须与 CPython 行为一致）
    check('_safe_name 合法名', runner._safe_name('hello_world2') == 'hello_world2')
    check('_safe_name 大写数字', runner._safe_name('AbC_09') == 'AbC_09')
    check('_safe_name 空串', runner._safe_name('') == '')
    check('_safe_name 下划线开头', runner._safe_name('_abc') == '')
    check('_safe_name 中文被拒', runner._safe_name('测试') == '')
    check('_safe_name 特殊字符被拒', runner._safe_name('a-b') == '')
    check('_safe_name 超长被拒', runner._safe_name('a' * 41) == '')

    # 12. 无 async def main 的异步程序 -> error 状态
    r = await cli.post('/api/programs', body={'name': 'nomain', 'code': '#type:async\nimport uvm\nprint(1)\n'})
    check('创建 no-main 异步程序', r.status_code == 200)
    r = await cli.post('/api/programs/nomain/start', body={})
    check('启动 no-main 异步程序', r.status_code == 200)
    for _ in range(60):
        st = manager.get_program('nomain')
        if st.status != 'running':
            break
        await asyncio.sleep(0.05)
    check('no-main 程序进入 error 状态', st.status == 'error', 'status=' + st.status)

    # 13. 同步程序协作式停止（uvm.should_stop）
    SYNC_LOOP = ("#type:sync\n"
                 "import uvm\n"
                 "while not uvm.should_stop():\n"
                 "    uvm.sleep_ms(30)\n"
                 "    print('sync-loop-tick')\n"
                 "print('sync-loop-stopped')\n")
    r = await cli.post('/api/programs', body={'name': 'syncloop', 'code': SYNC_LOOP})
    check('创建 sync 长循环', r.status_code == 200)
    r = await cli.post('/api/programs/syncloop/start', body={})
    check('启动 sync 长循环', r.status_code == 200, (r.text or '')[:120])
    await asyncio.sleep(0.1)
    check('sync 循环运行中', manager.is_running('syncloop'))
    r = await cli.post('/api/programs/syncloop/stop', body={})
    check('停止 sync 长循环', r.status_code == 200)
    for _ in range(60):
        st = manager.get_program('syncloop')
        if st.status != 'running':
            break
        await asyncio.sleep(0.05)
    check('sync 循环协作式停止', st.status == 'stopped', 'status=' + st.status)

    # 14. MAX_SYNC 并发上限
    r = await cli.post('/api/programs', body={'name': 'synca', 'code': SYNC_LOOP})
    check('创建 synca', r.status_code == 200)
    r = await cli.post('/api/programs', body={'name': 'syncb', 'code': SYNC_LOOP})
    check('创建 syncb', r.status_code == 200)
    r = await cli.post('/api/programs/synca/start', body={})
    check('启动 synca', r.status_code == 200)
    r = await cli.post('/api/programs/syncb/start', body={})
    check('启动 syncb', r.status_code == 200)
    r = await cli.post('/api/programs', body={'name': 'syncb2', 'code': SYNC_LOOP})
    check('创建 sand', r.status_code == 200)
    r = await cli.post('/api/programs/syncb2/start', body={})
    check('第三个同步程序被拒(上限2)', r.status_code == 400, (r.text or '')[:120])
    r = await cli.post('/api/programs/synca/stop', body={})
    r = await cli.post('/api/programs/syncb/stop', body={})
    for _ in range(60):
        a = manager.get_program('synca').status
        b = manager.get_program('syncb').status
        if a != 'running' and b != 'running':
            break
        await asyncio.sleep(0.05)
    check('synca/syncb 均已停止', a == 'stopped' and b == 'stopped',
          'a=%s b=%s' % (a, b))

    # 15. 运行中禁止删除/重命名
    r = await cli.post('/api/programs', body={'name': 'runningprog', 'code': ASYNC_CODE})
    check('创建 runningprog', r.status_code == 200)
    r = await cli.post('/api/programs/runningprog/start', body={})
    check('启动 runningprog', r.status_code == 200)
    await asyncio.sleep(0.2)
    check('runningprog 运行中', manager.is_running('runningprog'))
    r = await cli.delete('/api/programs/runningprog')
    check('运行中删除被拒', r.status_code == 400)
    r = await cli.post('/api/programs/runningprog/rename', body={'name': 'rp2'})
    check('运行中重命名被拒', r.status_code == 400)
    r = await cli.post('/api/programs/runningprog/stop', body={})
    for _ in range(60):
        st = manager.get_program('runningprog')
        if st.status != 'running':
            break
        await asyncio.sleep(0.05)
    r = await cli.delete('/api/programs/runningprog')
    check('停止后删除成功', r.status_code == 200)

    # 16. 静态文件路径穿越拒绝
    r = await cli.get('/../etc/passwd')
    check('GET /../ 被拒', r.status_code == 404)
    r = await cli.get('/%2e%2e%2fconfig.json')
    check('GET 编码穿越被拒', r.status_code == 404)

    # 16b. WiFi 扫描（PC 无 network 模块，应返回优雅错误而非崩溃）
    r = await cli.get('/api/scan')
    check('GET /api/scan 有响应', r.status_code in (200, 400))
    check('GET /api/scan 返回 dict', isinstance(r.json, dict))

    # 17. WebSocket Hub：历史回放 + 清空 + ping 应答（不依赖真实 socket）
    class FakeWS:
        def __init__(self):
            self.sent = []
            self.closed = False

        async def send(self, payload):
            self.sent.append(payload)

        async def receive(self):
            await asyncio.sleep(30)
            return None

        async def close(self):
            self.closed = True

        def _handle(self, ws, client, msg):
            return hub._handle(ws, client, msg)

    con._push('ws-history-line')
    fws = FakeWS()
    client = hub.register(fws)
    check('注册时回放历史', any('ws-history-line' in s for s in fws.sent) or
          any('ws-history-line' in s for s in client['queue']))
    hub._handle(fws, client, json.dumps({'type': 'clear'}))
    check('clear 后控制台清空', 'cleared' in client['queue'][-1])
    hub._handle(fws, client, json.dumps({'type': 'ping'}))
    check('ping 收到 pong', json.loads(client['queue'][-1]).get('type') == 'pong')

    # 18. 登出后 token 失效（在密码保护开启时）
    config.save({'wifi': {'ssid': '', 'password': ''},
                 'ap': {'ssid': 'T', 'password': ''},
                 'auth': {'enabled': True, 'password': 'secret'},
                 'autostart': []})
    r = await cli.post('/api/login', body={'password': 'secret'})
    check('B18 登录成功', r.status_code == 200 and r.json.get('token'))
    token2 = r.json['token']
    r = await cli.get('/api/programs', headers={'X-Auth-Token': token2})
    check('B18 带 token 可访问', r.status_code == 200)
    r = await cli.post('/api/logout', body={})
    check('B18 登出成功', r.status_code == 200)
    r = await cli.get('/api/programs', headers={'X-Auth-Token': token2})
    check('B18 登出后 token 失效', r.status_code == 401)
    config.save({'wifi': {'ssid': '', 'password': ''},
                 'ap': {'ssid': 'T', 'password': ''},
                 'auth': {'enabled': False, 'password': ''},
                 'autostart': []})

    # 19. 文件系统管理 / 远程更新
    fsroot = fsmgr.FS_ROOT
    os.makedirs(os.path.join(fsroot, 'lib', 'microdot'), exist_ok=True)
    os.makedirs(os.path.join(fsroot, 'www'), exist_ok=True)
    os.makedirs(os.path.join(fsroot, 'programs'), exist_ok=True)
    with open(os.path.join(fsroot, 'lib', 'hello.py'), 'wb') as f:
        f.write(b'print("hi")\n')
    with open(os.path.join(fsroot, 'config.json'), 'w') as f:
        f.write('{}\n')

    # 19a. 路径归一化
    check('normalize /lib/web.py', fsmgr.normalize('/lib/web.py') == '/lib/web.py')
    check('normalize /a/../b', fsmgr.normalize('/a/../b') == '/b')
    check('normalize 逃逸根 /.. 被拒', fsmgr.normalize('/..') is None)
    check('normalize 相对路径被拒', fsmgr.normalize('lib/x') is None)
    check('normalize 空路径被拒', fsmgr.normalize('') is None)
    check('normalize ./ 折叠', fsmgr.normalize('/a/./b') == '/a/b')

    # 19b. 危险文件判定
    check('危险: config.json', fsmgr.is_dangerous('/config.json') is True)
    check('危险: /lib/web.py', fsmgr.is_dangerous('/lib/web.py') is True)
    check('危险: /www/index.html', fsmgr.is_dangerous('/www/index.html') is True)
    check('危险: /main.py', fsmgr.is_dangerous('/main.py') is True)
    check('安全: /programs/x.py', fsmgr.is_dangerous('/programs/x.py') is False)

    # 19c. 目录列表
    r = await cli.get('/api/fs/list?path=/')
    check('fs list / 200', r.status_code == 200, (r.text or '')[:100])
    names0 = {e['name'] for e in r.json['entries']}
    check('fs list / 含 lib/www/programs/config.json',
          {'lib', 'www', 'programs', 'config.json'} <= names0, str(names0))
    check('fs list 返回 free/dangerous', 'free' in r.json and 'dangerous' in r.json)
    r = await cli.get('/api/fs/list?path=/lib')
    libnames = [e['name'] for e in r.json['entries']]
    check('fs list /lib 含 hello.py/microdot',
          'hello.py' in libnames and 'microdot' in libnames, str(libnames))
    r = await cli.get('/api/fs/list?path=/../x')
    check('fs list 穿越被拒', r.status_code == 400)

    # 19d. 读取
    r = await cli.get('/api/fs/read?path=/lib/hello.py')
    check('fs read hello.py', r.status_code == 200 and r.json.get('text') == 'print("hi")\n',
          (r.text or '')[:100])
    r = await cli.get('/api/fs/read?path=/lib/nonexist.py')
    check('fs read 不存在 404', r.status_code == 404)
    r = await cli.get('/api/fs/read?path=/lib')
    check('fs read 目录 400', r.status_code == 400)

    # 19e. 上传/覆盖（含自动建父目录）
    r = await cli.put('/api/fs/file?path=/programs/x.py',
                      body=b'x = 1\n', headers={'Content-Type': 'application/octet-stream'})
    check('fs put 新建文件', r.status_code == 200, (r.text or '')[:100])
    r = await cli.put('/api/fs/file?path=/programs/x.py',
                      body=b'x = 2\n', headers={'Content-Type': 'application/octet-stream'})
    check('fs put 覆盖文件', r.status_code == 200)
    r = await cli.get('/api/fs/read?path=/programs/x.py')
    check('fs put 覆盖生效', r.json.get('text') == 'x = 2\n')
    r = await cli.put('/api/fs/file?path=/lib/a/b/c.py',
                      body=b'deep\n', headers={'Content-Type': 'application/octet-stream'})
    check('fs put 自动建父目录', r.status_code == 200, (r.text or '')[:100])
    r = await cli.get('/api/fs/read?path=/lib/a/b/c.py')
    check('fs put 深层文件可读', r.json.get('text') == 'deep\n')
    r = await cli.put('/api/fs/file?path=/lib',
                      body=b'x', headers={'Content-Type': 'application/octet-stream'})
    check('fs put 写入目录被拒', r.status_code == 400)
    r = await cli.put('/api/fs/file?path=/lib/empty.txt', body=b'',
                      headers={'Content-Type': 'application/octet-stream'})
    check('fs put 空文件', r.status_code == 200)
    r = await cli.get('/api/fs/read?path=/lib/empty.txt')
    check('fs put 空文件可读', r.json.get('text') == '')

    # 19f. 大文件流式上传（>16KB 走 stream）
    big = b'big-data-line\n' * 16000  # ~176KB
    r = await cli.put('/api/fs/file?path=/lib/big.py', body=big,
                      headers={'Content-Type': 'application/octet-stream'})
    check('fs put 大文件(流式)', r.status_code == 200, (r.text or '')[:100])
    check('fs 大文件写盘字节数', fsmgr.size('/lib/big.py') == len(big),
          'size=%d want=%d' % (fsmgr.size('/lib/big.py'), len(big)))
    r = await cli.get('/api/fs/file?path=/lib/big.py')
    check('fs download 大文件 200', r.status_code == 200)
    check('fs download 内容一致', r.body == big)
    cd = r.headers.get('Content-Disposition', '')
    check('fs download 带 Content-Disposition', 'attachment' in cd, cd)

    # 19f2. 分段读取（前端循环 offset/limit 拼接）
    got = b''
    off = 0
    end = 0
    while True:
        r = await cli.get('/api/fs/read?path=/lib/big.py&offset=%d&limit=8192' % off)
        check('fs read 分段 %d 200' % off, r.status_code == 200, (r.text or '')[:80])
        j = r.json
        got += j['text'].encode('utf-8')
        end = j['offset']
        if j['done']:
            break
        off = j['offset']
    check('fs read 分段拼接 == 原文件', got == big,
          'len=%d want=%d' % (len(got), len(big)))
    check('fs read 分段 offset 推进到 EOF', end == len(big))

    # 19f3. UTF-8 字符边界分段（limit 故意切破多字节字符）
    uni = '中文字符串🙂测试abc'.encode('utf-8')
    with open(os.path.join(fsroot, 'lib', 'uni.py'), 'wb') as f:
        f.write(uni)
    joined = b''
    off = 0
    while True:
        r = await cli.get('/api/fs/read?path=/lib/uni.py&offset=%d&limit=7' % off)
        check('fs read UTF-8 分段 %d 200' % off, r.status_code == 200, (r.text or '')[:80])
        j = r.json
        joined += j['text'].encode('utf-8')
        if j['done']:
            break
        off = j['offset']
    check('fs read UTF-8 边界分段无损', joined == uni,
          'joined=%r want=%r' % (joined, uni))

    # 19f4. 分段写入（前端分片 PUT append=0/1 + final=1）
    CH = 8192
    for i in range(0, len(big), CH):
        chunk = big[i:i + CH]
        append = '0' if i == 0 else '1'
        final = '1' if i + CH >= len(big) else '0'
        r = await cli.put(
            '/api/fs/file?path=/programs/big.py&append=%s&final=%s' % (append, final),
            body=chunk, headers={'Content-Type': 'application/octet-stream'})
        check('fs put 分片 %d 200' % i, r.status_code == 200, (r.text or '')[:80])
    check('fs put 分片写盘字节数', fsmgr.size('/programs/big.py') == len(big),
          'size=%d want=%d' % (fsmgr.size('/programs/big.py'), len(big)))
    with open(os.path.join(fsroot, 'programs', 'big.py'), 'rb') as f:
        check('fs put 分片内容一致', f.read() == big)

    # 19f5. 超过 fs_edit_max（512KB）仍 413
    huge = b'x' * (600 * 1024)
    with open(os.path.join(fsroot, 'lib', 'huge.py'), 'wb') as f:
        f.write(huge)
    r = await cli.get('/api/fs/read?path=/lib/huge.py')
    check('fs read 超限 413', r.status_code == 413)

    # 19g. mkdir
    r = await cli.post('/api/fs/mkdir?path=/lib/newdir', body={})
    check('fs mkdir', r.status_code == 200, (r.text or '')[:100])
    check('fs mkdir 后存在', fsmgr.is_dir('/lib/newdir'))
    r = await cli.post('/api/fs/mkdir?path=/lib/newdir', body={})
    check('fs mkdir 已存在 400', r.status_code == 400)
    r = await cli.post('/api/fs/mkdir?path=/..', body={})
    check('fs mkdir 非法路径 400', r.status_code == 400)

    # 19h. rename（危险路径需 force）
    r = await cli.post('/api/fs/rename', body={'from': '/programs/x.py', 'to': '/programs/y.py'})
    check('fs rename 普通文件', r.status_code == 200, (r.text or '')[:100])
    check('fs rename 后存在', fsmgr.exists('/programs/y.py'))
    r = await cli.post('/api/fs/rename', body={'from': '/config.json', 'to': '/cfg.json'})
    check('fs rename 危险无force被拒', r.status_code == 400)
    r = await cli.post('/api/fs/rename', body={'from': '/config.json', 'to': '/cfg.json', 'force': True})
    check('fs rename 危险带force成功', r.status_code == 200, (r.text or '')[:100])
    check('fs rename 后 cfg.json 存在', fsmgr.exists('/cfg.json'))

    # 19i. delete（危险路径需 force；目录需 recursive）
    r = await cli.post('/api/fs/delete?path=/programs/y.py', body={})
    check('fs delete 文件', r.status_code == 200)
    check('fs delete 后不存在', not fsmgr.exists('/programs/y.py'))
    r = await cli.post('/api/fs/mkdir?path=/programs/nd', body={})
    check('fs delete 前建空目录', r.status_code == 200)
    r = await cli.post('/api/fs/delete?path=/programs/nd', body={})
    check('fs delete 空目录', r.status_code == 200)
    os.makedirs(os.path.join(fsroot, 'lib', 'r'), exist_ok=True)
    with open(os.path.join(fsroot, 'lib', 'r', 'inner.txt'), 'w') as f:
        f.write('x')
    r = await cli.post('/api/fs/delete?path=/lib/r', body={})
    check('fs delete 危险无force被拒', r.status_code == 400)
    r = await cli.post('/api/fs/delete?path=/lib/r&force=1', body={})
    check('fs delete 非空目录无recursive被拒', r.status_code == 400)
    r = await cli.post('/api/fs/delete?path=/lib/r&recursive=1&force=1', body={})
    check('fs delete 非空目录递归(带force)', r.status_code == 200)
    check('fs delete 递归后目录不存在', not fsmgr.exists('/lib/r'))
    r = await cli.post('/api/fs/delete?path=/www', body={})
    check('fs delete 危险无force被拒', r.status_code == 400)
    r = await cli.post('/api/fs/delete?path=/www&force=1&recursive=1', body={})
    check('fs delete 危险带force递归成功', r.status_code == 200)
    r = await cli.post('/api/fs/delete?path=/', body={})
    check('fs delete 根目录被拒', r.status_code == 400)

    print('---')
    print('passed=%d failed=%d' % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))