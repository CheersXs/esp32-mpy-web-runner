#!/usr/bin/env python3
"""PC 端冒烟测试：不依赖板子，用 CPython + microdot 测试客户端把
REST API 和 asyncio/线程调度逻辑跑一遍。

用法:  python tools/smoke_test.py
（可选环境变量 RUN_WITH_LINE=1 在最后再跑一遍单元冒烟）
"""
import os
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))

import asyncio  # noqa: E402

import config  # noqa: E402
import console  # noqa: E402
import runner  # noqa: E402
import web  # noqa: E402

TMP = tempfile.mkdtemp(prefix='esp32wr_')
config.CONFIG_PATH = os.path.join(TMP, 'config.json')
runner.PROGRAMS_DIR = os.path.join(TMP, 'programs')
web.WWW_DIR = os.path.join(ROOT, 'www')
web.CM_DIR = os.path.join(web.WWW_DIR, 'cm')


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

    print('---')
    print('passed=%d failed=%d' % (passed, failed))
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))