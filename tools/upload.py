#!/usr/bin/env python3
"""一键把 esp32-web-runner 项目上传到 ESP32（依赖 mpremote）。

用法:
    python tools/upload.py --target esp32s3          # 上传到 ESP32-S3（默认）
    python tools/upload.py --target esp32c3          # 上传到 ESP32-C3
    python tools/upload.py --port COM7               # 指定串口
    python tools/upload.py --no-examples             # 不覆盖 programs/ 里的示例

首次使用先装 mpremote:
    pip install mpremote
"""
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 共享层（S3/C3 通用）
SHARED_DIRS = [
    ('lib', '/lib'),
    ('www', '/www'),
]

# microdot：S3 全量；C3 只传运行必需（省 flash）
MICRODOT_FULL = ['__init__.py', 'microdot.py', 'helpers.py',
                 'websocket.py', 'cors.py', 'test_client.py']
MICRODOT_MIN = ['__init__.py', 'microdot.py', 'helpers.py', 'websocket.py']


def check_mpremote():
    return 'mpremote' if shutil.which('mpremote') else None


def run(cmd, port, remote=False):
    args = ['mpremote']
    if remote:
        args.append('connect')
    if remote and port:
        args.append(port)
    args += cmd
    return subprocess.run(args, capture_output=True, text=True)


def mkdir(port, path):
    return run(['fs', 'mkdir', path], port, remote=True)


def upload_file(port, local, remote):
    r = run(['fs', 'cp', local, ':' + remote], port, remote=True)
    if r.returncode != 0:
        print('  ! 上传失败 %s -> %s: %s' % (local, remote, r.stderr.strip()))
        return False
    return True


def upload_dir(port, local_dir, remote_dir, skip=(), skip_dirs=()):
    for dirpath, dirnames, filenames in os.walk(local_dir):
        # 跳过指定子目录（如 microdot 单独按目标裁剪上传）
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for sub in dirnames:
            rel = os.path.relpath(os.path.join(dirpath, sub), local_dir).replace(os.sep, '/')
            mkdir(port, remote_dir + '/' + rel)
        for fn in filenames:
            if fn.endswith(('.pyc', '.mjs')) or fn in skip:
                continue
            local = os.path.join(dirpath, fn)
            rel = os.path.relpath(local, local_dir).replace(os.sep, '/')
            remote = remote_dir + '/' + rel
            upload_file(port, local, remote)


def upload_microdot(port, target):
    names = MICRODOT_FULL if target == 'esp32s3' else MICRODOT_MIN
    for fn in names:
        upload_file(port, os.path.join(ROOT, 'lib', 'microdot', fn),
                    '/lib/microdot/' + fn)


def write_config(port, target):
    """预置 config.json。C3：ap.enabled=false + 预填 WiFi（读 c3_config.py）。"""
    cfg = {
        'wifi': {'ssid': '', 'password': ''},
        'ap': {'enabled': True, 'ssid': 'ESP32-S3', 'password': ''},
        'auth': {'enabled': False, 'password': ''},
        'autostart': [],
    }
    if target == 'esp32c3':
        cfg['ap']['enabled'] = False
        # 从 c3_config.py 读取 WiFi（PC 端 import 无副作用，仅定义变量）
        try:
            c3 = os.path.join(ROOT, 'targets', 'esp32c3', 'c3_config.py')
            spec = importlib.util.spec_from_file_location('c3_config', c3)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            cfg['wifi']['ssid'] = getattr(mod, 'WIFI_SSID', '')
            cfg['wifi']['password'] = getattr(mod, 'WIFI_PASS', '')
        except Exception as e:
            print('  ! 读取 c3_config.py 失败（WiFi 留空）: %r' % (e,))
    # 写临时文件再上传
    tmp = os.path.join(ROOT, 'config.json.tmp')
    with open(tmp, 'w') as f:
        json.dump(cfg, f)
    ok = upload_file(port, tmp, '/config.json')
    try:
        os.remove(tmp)
    except OSError:
        pass
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--target', default='esp32s3',
                    choices=['esp32s3', 'esp32c3'],
                    help='目标板：esp32s3（默认）或 esp32c3')
    ap.add_argument('--port', default=None, help='串口，如 COM7')
    ap.add_argument('--no-examples', action='store_true',
                    help='不覆盖板上的示例程序')
    args = ap.parse_args()

    if not check_mpremote():
        sys.exit('未找到 mpremote，请先运行:  pip install mpremote')

    target = args.target
    tdir = os.path.join(ROOT, 'targets', target)
    print('目标板: %s' % target)

    # 建立目录
    for _, rpath in SHARED_DIRS:
        print('mkdir', rpath)
        mkdir(args.port, rpath)
    mkdir(args.port, '/lib/microdot')
    mkdir(args.port, '/programs')

    # 上传共享 lib / www（microdot 单独按目标裁剪上传）
    for ldir, rdir in SHARED_DIRS:
        skip = ()
        skip_dirs = ('microdot',)
        if target == 'esp32c3' and rdir == '/www':
            # C3 用内联单连接页面：codemirror 等独立静态资源不再需要
            skip = ('app.js', 'style.css')
            skip_dirs = ('microdot', 'cm')
        upload_dir(args.port, os.path.join(ROOT, ldir), rdir,
                   skip=skip, skip_dirs=skip_dirs)

    # microdot（按目标裁剪）
    upload_microdot(args.port, target)

    # 上传目标板 main.py / boot.py
    upload_file(args.port, os.path.join(tdir, 'main.py'), '/main.py')
    upload_file(args.port, os.path.join(tdir, 'boot.py'), '/boot.py')

    # C3 专属：c3_config.py + 专属示例
    if target == 'esp32c3':
        upload_file(args.port, os.path.join(tdir, 'c3_config.py'),
                    '/c3_config.py')
        # C3 内联单连接页面（覆盖共享的多文件 index.html）
        inline = os.path.join(tdir, 'www', 'index.html')
        if os.path.exists(inline):
            print('上传 C3 内联页面 -> /www/index.html')
            upload_file(args.port, inline, '/www/index.html')
        ex = os.path.join(tdir, 'examples')
        if os.path.isdir(ex):
            for fn in os.listdir(ex):
                if fn.endswith('.py'):
                    print('上传 C3 示例  %s -> /programs/%s' % (fn, fn))
                    upload_file(args.port, os.path.join(ex, fn),
                                '/programs/' + fn)

    # 共享示例程序（默认上传，可用 --no-examples 跳过）
    if not args.no_examples:
        ex = os.path.join(ROOT, 'programs', 'examples')
        for fn in os.listdir(ex):
            if fn.endswith('.py'):
                print('上传示例  examples/%s -> /programs/%s' % (fn, fn))
                upload_file(args.port, os.path.join(ex, fn),
                            '/programs/' + fn)

    # 预置 config.json（C3 关闭 AP + 预填 WiFi）
    write_config(args.port, target)

    print('---')
    print('上传完成。现在软复位板子让它加载新系统 ...')
    run(['reset'], args.port, remote=True)
    print('重启中。C3 的 IP 见 OLED 屏幕；S3 见串口/网页控制台。')


if __name__ == '__main__':
    main()