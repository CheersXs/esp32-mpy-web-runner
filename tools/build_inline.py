#!/usr/bin/env python3
"""为 ESP32-C3 生成内联单连接页面。

C3 射频弱、内存紧，浏览器并发拉取 10 个静态文件（~450KB）经常握手失败。
本工具把 www/index.html 引用的 CSS 和功能脚本内联成一个 HTML 文件，
让浏览器只发 1 个请求。CodeMirror（~170KB）体积太大，不内联：
改由 build_cm.py 合并并切成 gzip 分片（cm-partK.js.gz），app.js 启动后
按序 fetch 拼接 eval，编辑器先以 textarea 兜底，包到达后再原地升级。
S3 仍使用原多文件页面。

用法:
    python tools/build_inline.py
输出:
    targets/esp32c3/www/index.html      内联核心（~79KB）
（CodeMirror 分片由 tools/build_cm.py 单独生成，本脚本不触碰 cm/ 目录）
"""
import os
import re

from build_cm import CM_PARTS, CM_SCRIPTS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WWW = os.path.join(ROOT, 'www')
OUT_DIR = os.path.join(ROOT, 'targets', 'esp32c3', 'www')
OUT = os.path.join(OUT_DIR, 'index.html')


def _read(path, what):
    with open(path, 'rb') as f:
        data = f.read()
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        print('  ! %s 非 UTF-8，按 latin-1 内联（内容可能乱码）' % what)
        return data.decode('latin-1')


def _guard(text, what):
    # JS/CSS 内容里出现这些字样会被浏览器提前终止标签
    if '</script' in text.lower() or '</style' in text.lower() or \
            '<script' in text.lower() or '<style' in text.lower():
        print('  ! %s 内含有 <script>/<style> 字样（已转义 </...>）' % what)
        text = text.replace('</script', '<\\/script').replace(
            '</style', '<\\/style')
    return text


def main():
    html = _read(os.path.join(WWW, 'index.html'), 'index.html')

    def inline_asset(src, what):
        path = os.path.join(WWW, src.lstrip('/'))
        if not os.path.exists(path):
            print('  ! 缺少资源: %s' % src)
            return None
        body = _guard(_read(path, what), what)
        print('  内联 %-32s %6d B' % (src, len(body)))
        return body

    def link_repl(m):
        src = m.group(1)
        body = inline_asset(src, 'CSS')
        if body is None:
            return m.group(0)
        return '<style>\n' + body + '\n</style>'

    def script_repl(m):
        src = m.group(1)
        if src in CM_SCRIPTS:
            print('  跳过 %-32s -> cm-partK.js.gz（build_cm.py 延迟加载）' % src)
            return ''
        body = inline_asset(src, 'JS')
        if body is None:
            return m.group(0)
        return '<script>\n' + body + '\n</script>'

    html = re.sub(
        r'<link[^>]+rel="stylesheet"[^>]+href="([^"]+)"[^>]*>',
        link_repl, html, flags=re.IGNORECASE)
    html = re.sub(
        r'<script[^>]+src="([^"]+)"[^>]*>\s*</script>',
        script_repl, html, flags=re.IGNORECASE)

    leftover = re.findall(r'<(?:(?:link)|(?:script))[^>]+(?:src|href)="[^"]+"',
                          html, flags=re.IGNORECASE)
    if leftover:
        print('  ! 仍有外部引用未被内联: %r' % (leftover,))

    if not html.strip().lower().endswith('</html>'):
        print('  ! 输出不以 </html> 结尾，可能不完整')

    # 分片数注入：C3 把合并包切成 CM_PARTS 片逐个 fetch，app.js 里默认 4，
    # 生成内联页时按实际值替换，保证两端一致。
    html = html.replace('var CM_PARTS = 4;', 'var CM_PARTS = %d;' % CM_PARTS, 1)

    out_dir = os.path.dirname(OUT)
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    with open(OUT, 'wb') as f:
        f.write(html.encode('utf-8'))
    print('已生成 %s (%d B)' % (OUT, len(html.encode('utf-8'))))
    print('CodeMirror 分片（cm-partK.js.gz）请运行 tools/build_cm.py 单独生成')


if __name__ == '__main__':
    main()