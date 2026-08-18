"""文件系统管理模块：为网页文件管理器 + 远程更新提供安全的基础文件操作。

- 所有路径以 '/' 开头的设备绝对路径为准（如 /lib/web.py），操作前统一归一化，
  拒绝 '..' 逃逸根目录。
- FS_ROOT 用于 PC 端冒烟测试：默认 ''（真实根目录），测试时可指向临时目录，
  让测试完全不碰真实文件系统。
- 危险文件（启动关键文件 / lib / www 应用层）删除、重命名需带 force=1，
  由调用方（web.py 路由）校验。
- 大文件写入走"临时文件 + 覆盖 + rename"的原子替换，避免写一半崩溃损坏文件。
"""

import os

FS_ROOT = ''

# 启动关键文件：编辑强警告，删除/重命名需 force
BOOT_FILES = ('/main.py', '/boot.py', '/c3_config.py', '/config.json')
# 应用层目录前缀：改动需重启才生效，删除/重命名需 force
APP_DIRS = ('/lib', '/www')

_CHUNK = 1024


# ---------- 路径处理 ----------

def normalize(path):
    """归一化设备绝对路径；非法（空/逃逸根/含 NUL）返回 None。"""
    if not path or not isinstance(path, str):
        return None
    if not path.startswith('/'):
        return None
    if '\x00' in path:
        return None
    parts = []
    for p in path.split('/'):
        if p == '' or p == '.':
            continue
        if p == '..':
            if parts:
                parts.pop()
            else:
                return None
        else:
            parts.append(p)
    out = '/' + '/'.join(parts)
    return out


def _real(path):
    """把设备绝对路径映射到 FS_ROOT 下的真实路径（测试隔离用）。"""
    return FS_ROOT + path


def is_dangerous(path):
    """是否为系统关键文件/应用层文件（删除/重命名需 force）。"""
    p = normalize(path)
    if p is None:
        return False
    if p in BOOT_FILES:
        return True
    for d in APP_DIRS:
        if p == d or p.startswith(d + '/'):
            return True
    return False


def ensure_parent(path):
    """确保父目录存在（不存在则逐级创建）。"""
    real = _real(path)
    parent = os.path.dirname(real)
    missing = []
    cur = parent
    while cur and not os.path.exists(cur):
        missing.append(cur)
        nxt = os.path.dirname(cur)
        if nxt == cur:
            break
        cur = nxt
    for d in reversed(missing):
        try:
            os.mkdir(d)
        except OSError:
            pass


def _is_dir(path):
    try:
        st = os.stat(path)
        return (st[0] & 0x4000) != 0
    except OSError:
        return False


def _commit(tmp, real):
    """原子替换：删旧文件再改名（MicroPython os.rename 在目标存在时会失败）。"""
    try:
        os.remove(real)
    except OSError:
        pass
    os.rename(tmp, real)


# ---------- 查询 ----------

def exists(path):
    p = normalize(path)
    if p is None:
        return False
    return os.path.exists(_real(p))


def size(path):
    p = normalize(path)
    if p is None:
        return -1
    try:
        return os.stat(_real(p))[6]
    except OSError:
        return -1


def is_dir(path):
    p = normalize(path)
    if p is None:
        return False
    return _is_dir(_real(p))


def list_dir(path):
    """返回 {path, entries}；entries 为 [{name, dir, size}]，目录在前字母序。"""
    p = normalize(path)
    if p is None:
        raise ValueError('bad path')
    real = _real(p)
    entries = []
    for name in os.listdir(real):
        full = real if real.endswith('/') else real + '/'
        full += name
        try:
            st = os.stat(full)
            entries.append({
                'name': name,
                'dir': (st[0] & 0x4000) != 0,
                'size': st[6],
            })
        except OSError:
            continue
    entries.sort(key=lambda e: (not e['dir'], e['name'].lower()))
    return {'path': p, 'entries': entries}


def read_text(path):
    """读取文件文本（UTF-8）。调用方应先检查 size 上限。"""
    p = normalize(path)
    if p is None:
        raise ValueError('bad path')
    with open(_real(p), 'r') as f:
        return f.read()


def read_range(path, offset, limit):
    """按字节区间读取，回退到 UTF-8 字符边界后解码。

    返回 (text, end)：end 是实际结束的字节偏移（<= offset+limit），
    供前端以此为下一次 offset 续读；跨段拼接无损。
    """
    p = normalize(path)
    if p is None:
        raise ValueError('bad path')
    if offset < 0 or limit <= 0:
        raise ValueError('bad range')
    real = _real(p)
    if _is_dir(real):
        raise OSError('is a directory')
    with open(real, 'rb') as f:
        f.seek(offset)
        data = f.read(limit)
    if not data:
        return '', offset
    while data:
        try:
            text = data.decode('utf-8')
            break
        except UnicodeDecodeError:
            data = data[:-1]
    else:  # pragma: no cover
        raise ValueError('file is not valid UTF-8')
    return text, offset + len(data)


# ---------- 写入 / 上传 ----------

def write_bytes(path, data):
    """整块字节写入（小文件，请求体已在内存时用）。"""
    p = normalize(path)
    if p is None:
        raise ValueError('bad path')
    real = _real(p)
    if _is_dir(real):
        raise OSError('is a directory')
    ensure_parent(p)
    tmp = real + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(data)
    _commit(tmp, real)


async def write_stream(path, stream, chunk=_CHUNK):
    """从异步流分块写入（大文件，内存安全）。stream 需支持 await read(n)。"""
    p = normalize(path)
    if p is None:
        raise ValueError('bad path')
    real = _real(p)
    if _is_dir(real):
        raise OSError('is a directory')
    ensure_parent(p)
    tmp = real + '.tmp'
    f = open(tmp, 'wb')
    try:
        while True:
            data = await stream.read(chunk)
            if not data:
                break
            f.write(data)
    finally:
        f.close()
    _commit(tmp, real)


def write_append(path, data, append=False, final=False):
    """分片追加写入：append=False 打开 .tmp 覆盖，True 追加到 .tmp；
    final=True 时把 .tmp 提交为正式文件。前端严格顺序分片调用。"""
    p = normalize(path)
    if p is None:
        raise ValueError('bad path')
    real = _real(p)
    if _is_dir(real):
        raise OSError('is a directory')
    ensure_parent(p)
    tmp = real + '.tmp'
    with open(tmp, 'ab' if append else 'wb') as f:
        f.write(data)
    if final:
        _commit(tmp, real)


# ---------- 目录 / 重命名 / 删除 ----------

def mkdir(path):
    p = normalize(path)
    if p is None or p == '/':
        raise ValueError('bad path')
    ensure_parent(p)
    os.mkdir(_real(p))


def rename(src, dst):
    s = normalize(src)
    d = normalize(dst)
    if s is None or d is None or s == '/' or d == '/':
        raise ValueError('bad path')
    sr, dr = _real(s), _real(d)
    if _is_dir(sr) and not _is_dir(dr):
        try:
            st = os.stat(dr)
            raise OSError('target exists')
        except OSError:
            pass
    ensure_parent(d)
    try:
        os.rename(sr, dr)
    except OSError:
        raise ValueError('rename failed (target may already exist)')


def delete(path, recursive=False):
    p = normalize(path)
    if p is None or p == '/':
        raise ValueError('bad path')
    real = _real(p)
    if not os.path.exists(real):
        raise OSError('not found')
    if _is_dir(real):
        if not recursive:
            try:
                os.rmdir(real)
            except OSError:
                raise ValueError('directory not empty (need recursive)')
        else:
            _rmtree(real)
    else:
        os.remove(real)


def _rmtree(path):
    for name in os.listdir(path):
        full = path + '/' + name
        if _is_dir(full):
            _rmtree(full)
        else:
            os.remove(full)
    os.rmdir(path)
