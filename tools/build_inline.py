#!/usr/bin/env python3
"""为 ESP32-C3 生成内联单连接页面。

C3 射频弱、内存紧，浏览器并发拉取 10 个静态文件（~450KB）经常握手失败。
本工具把 www/index.html 引用的 CSS 和功能脚本内联成一个 HTML 文件，
让浏览器只发 1 个请求。CodeMirror（~170KB）体积太大，不内联：
改为合并成 cm-bundle.js，由 app.js 在页面启动后延迟加载并自动重试，
编辑器先以 textarea 兜底，包到达后再原地升级。S3 仍使用原多文件页面。

用法:
    python tools/build_inline.py
输出:
    targets/esp32c3/www/index.html      内联核心（~79KB）
    targets/esp32c3/www/cm/cm-bundle.js  延迟加载的 CodeMirror 合并包（~193KB）
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WWW = os.path.join(ROOT, 'www')
OUT_DIR = os.path.join(ROOT, 'targets', 'esp32c3', 'www')
OUT = os.path.join(OUT_DIR, 'index.html')

# C3 不内联的 CodeMirror 脚本（顺序即依赖顺序），合并为 cm-bundle.js
CM_SCRIPTS = (
    '/cm/codemirror.min.js',
    '/cm/python.min.js',
    '/cm/closebrackets.min.js',
    '/cm/show-hint.min.js',
    '/cm/anyword-hint.js',
)

# 合并包切分数：C3 弱射频 + 小 lwIP pbuf，17KB 单次传输都会耗尽缓冲导致
# 其他请求全挂；切成 ~8KB 分片 + 前端片间强制间隔（pbuf 释放窗口）。
# S3 不受影响。
CM_PARTS = 8


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
            print('  跳过 %-32s -> cm-bundle.js（延迟加载）' % src)
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

    # 生成延迟加载的 CodeMirror 合并包（保持依赖顺序）
    parts = []
    for src in CM_SCRIPTS:
        p = os.path.join(WWW, src.lstrip('/'))
        if not os.path.exists(p):
            print('  ! 缺少资源: %s' % src)
            continue
        parts.append(_guard(_read(p, 'JS'), 'JS'))
    bundle = '\n;\n'.join(parts) + '\n'
    bundle_out = os.path.join(OUT_DIR, 'cm', 'cm-bundle.js')
    os.makedirs(os.path.dirname(bundle_out), exist_ok=True)
    raw = bundle.encode('utf-8')
    with open(bundle_out, 'wb') as f:
        f.write(raw)
    print('已生成 %s (%d B)' % (bundle_out, len(raw)))

    # 预压缩 cm-bundle.js.gz：C3 扛不住 ~193KB 单次传输（打开编辑器即压垮
    # 网络栈），gzip 后 ~35KB 比内联页还小。web.py 对 /cm/* 优先返回 .gz
    # 并带 Content-Encoding:gzip，浏览器自动解压，纯静态资源不影响板上更新。
    import gzip as _gzip
    gz = _gzip.compress(raw)
    gz_out = bundle_out + '.gz'
    with open(gz_out, 'wb') as f:
        f.write(gz)
    print('已生成 %s (%d B, gzip %d B, %.1f%%)' %
          (gz_out, len(raw), len(gz), 100.0 * len(gz) / len(raw)))

    # 分片（cm-partK.js.gz，K=0..CM_PARTS-1）：C3 弱射频连 65KB 单次 gzip
    # 传输都会停滞（请求长期 pending），切成多个 ~16KB 分片由 app.js 逐个
    # fetch（每片小传输稳定），拼接后全局 eval。切点任意——分片只是传输
    # 手段，拼接顺序还原原文即完整 JS。web.py 的 /cm/*.gz 分支同样命中。
    # 切分必须按 UTF-8 字符边界（bundle 为合法 UTF-8）：若按字节切破多字节
    # 字符，浏览器对单片 UTF-8 解码会用替换符损坏内容，拼接后 eval 失败。
    n = len(bundle)
    for k in range(CM_PARTS):
        a = k * n // CM_PARTS
        b = (k + 1) * n // CM_PARTS
        chunk = bundle[a:b].encode('utf-8')
        pjs = os.path.join(OUT_DIR, 'cm', 'cm-part%d.js' % k)
        with open(pjs, 'wb') as f:
            f.write(chunk)
        pz = pjs + '.gz'
        with open(pz, 'wb') as f:
            f.write(_gzip.compress(chunk))
        print('已生成 %s (%d B, gzip %d B)' %
              (pz, len(chunk), os.path.getsize(pz)))


if __name__ == '__main__':
    main()