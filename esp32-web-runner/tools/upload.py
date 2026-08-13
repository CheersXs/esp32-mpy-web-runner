#!/usr/bin/env python3
"""一键把 esp32-web-runner 项目上传到 ESP32（依赖 mpremote）。

用法:
    python tools/upload.py                # 自动找串口
    python tools/upload.py --port COM7    # 指定串口
    python tools/upload.py --no-examples  # 不覆盖 programs/ 里的示例

首次使用先装 mpremote:
    pip install mpremote
"""
import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (本地相对路径, 板上路径)
FILES = [
    ('boot.py', '/boot.py'),
    ('main.py', '/main.py'),
]

DIRS = [
    ('lib', '/lib'),
    ('lib/microdot', '/lib/microdot'),
    ('www', '/www'),
    ('www/cm', '/www/cm'),
    ('programs/examples', '/programs'),
]

WALK_DIRS = [('lib', '/lib'), ('www', '/www')]


def check_mpremote():
    if shutil.which('mpremote'):
        return 'mpremote'
    return None


def run(cmd, port, remote=False):
    args = ['mpremote']
    if remote:
        args.append('connect')
    if remote and port:
        args.append(port)
    args += cmd
    r = subprocess.run(args, capture_output=True, text=True)
    return r


def mkdir(port, path):
    # mpremote fs mkdir 已存在时不算致命；远程路径需带 ':' 前缀
    return run(['fs', 'mkdir', ':', path], port, remote=True)


def upload_file(port, local, remote):
    # mpremote 1.28: 远程路径必须显式带 ':' 前缀，否则视为本地路径
    r = run(['fs', 'cp', local, ':' + remote], port, remote=True)
    if r.returncode != 0:
        print('  ! 上传失败 %s -> %s: %s' % (local, remote, r.stderr.strip()))
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', default=None, help='串口，如 COM7')
    ap.add_argument('--no-examples', action='store_true',
                    help='不覆盖板上的示例程序')
    args = ap.parse_args()

    if not check_mpremote():
        sys.exit('未找到 mpremote，请先运行:  pip install mpremote')

    # 建立目录
    for _, rpath in DIRS:
        print('mkdir', rpath)
        mkdir(args.port, rpath)

    # 上传根文件
    for lpath, rpath in FILES:
        print('上传', lpath)
        upload_file(args.port, os.path.join(ROOT, lpath), rpath)

    # 上传 lib / www 整目录
    for ldir, rdir in WALK_DIRS:
        for dirpath, _dirnames, filenames in os.walk(os.path.join(ROOT, ldir)):
            for fn in filenames:
                if fn.endswith(('.pyc', '.mjs')):
                    continue
                local = os.path.join(dirpath, fn)
                rel = os.path.relpath(local, ROOT).replace(os.sep, '/')
                remote = '/' + rel
                upload_file(args.port, local, remote)

    # 示例程序（默认上传，可用 --no-examples 跳过）
    if not args.no_examples:
        ex = os.path.join(ROOT, 'programs', 'examples')
        for fn in os.listdir(ex):
            if fn.endswith('.py'):
                print('上传示例  examples/%s -> /programs/%s' % (fn, fn))
                upload_file(args.port, os.path.join(ex, fn),
                            '/programs/' + fn)

    print('---')
    print('上传完成。现在软复位板子让它加载新系统 ...')
    run(['reset'], args.port, remote=True)
    print('重启中。热点 / 地址见串口或网页控制台。')


if __name__ == '__main__':
    main()