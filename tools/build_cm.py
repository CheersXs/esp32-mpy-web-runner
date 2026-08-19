#!/usr/bin/env python3
"""为 ESP32-C3 生成 CodeMirror 延迟加载分片（cm-partK.js.gz）。

C3 弱射频 + 小 lwIP pbuf：~193KB 的 CodeMirror 单次传输会压垮网络栈，
本工具把 www/cm 下的 CodeMirror 源脚本按依赖顺序合并，预压缩 gzip 后
切成 CM_PARTS 个小片，由 app.js 启动后按序 fetch 拼接 eval。

与 build_inline.py 分开：cm 分片只依赖 www/cm 下的源文件，改 app.js /
index.html / style.css 时无需重新生成，只有动 CodeMirror 源文件才重跑。

用法:
    python tools/build_cm.py
输出（唯一产物）:
    targets/esp32c3/www/cm/cm-part0..7.js.gz   板上实际使用的分片

中间产物（cm-bundle.js / cm-bundle.js.gz / cm-partK.js）不落盘，历史残留
文件在每次运行时一并清除。
"""
import gzip
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WWW = os.path.join(ROOT, 'www')
OUT_DIR = os.path.join(ROOT, 'targets', 'esp32c3', 'www', 'cm')

# C3 不内联的 CodeMirror 脚本（顺序即依赖顺序），合并后切片
CM_SCRIPTS = (
    '/cm/codemirror.min.js',
    '/cm/python.min.js',
    '/cm/closebrackets.min.js',
    '/cm/show-hint.min.js',
    '/cm/anyword-hint.js',
)

# 合并包切分数：C3 弱射频 + 小 lwIP pbuf，17KB 单次传输都会耗尽缓冲导致
# 其他请求全挂；切成 ~8KB 分片 + 前端片间强制间隔（pbuf 释放窗口）。
# 与 upload.py 的分片循环、build_inline.py 注入前端的 CM_PARTS 保持一致。
CM_PARTS = 8


def _read(path):
    with open(path, 'rb') as f:
        data = f.read()
    return data.decode('utf-8')


def _guard(text):
    # JS 内容里出现这些字样会被浏览器提前终止标签
    if '</script' in text.lower() or '<script' in text.lower():
        print('  ! 内容含有 <script> 字样（已转义 </...>）')
        text = text.replace('</script', '<\\/script')
    return text


def main():
    parts = []
    for src in CM_SCRIPTS:
        p = os.path.join(WWW, src.lstrip('/'))
        if not os.path.exists(p):
            print('  ! 缺少资源: %s' % src)
            continue
        parts.append(_guard(_read(p)))
    # bundle 保持为 str：切片按字符边界（UTF-8 安全），避免切破多字节字符
    # 导致浏览器单片解码出替换符、拼接后 eval 失败（注意事项 §12）。
    bundle = '\n;\n'.join(parts) + '\n'
    n = len(bundle)
    print('合并 %d 个脚本 -> %d B，切 %d 片' % (len(parts), n, CM_PARTS))

    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)

    # 清理历史中间产物（cm-bundle.js(.gz)、未压缩 cm-partK.js），只留 .gz 分片
    for fn in os.listdir(OUT_DIR):
        if fn.endswith('.js') or fn.endswith('.js.gz'):
            try:
                os.remove(os.path.join(OUT_DIR, fn))
            except OSError:
                pass

    for k in range(CM_PARTS):
        a = k * n // CM_PARTS
        b = (k + 1) * n // CM_PARTS
        chunk = bundle[a:b].encode('utf-8')
        pz = os.path.join(OUT_DIR, 'cm-part%d.js.gz' % k)
        with open(pz, 'wb') as f:
            f.write(gzip.compress(chunk))
        print('已生成 %s (%d B, gzip %d B)' % (pz, len(chunk), os.path.getsize(pz)))


if __name__ == '__main__':
    main()