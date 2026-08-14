import sys

try:
    import io
except ImportError:
    io = None

try:
    import os
except ImportError:
    os = None

import config

MAX_LINES = config.console_max_lines()


class Console(io.IOBase if (io and hasattr(io, 'IOBase')) else object):
    """全局控制台：接管 print 输出，缓存最近日志并转发给订阅者(WebSocket)。

    平台差异：CPython 可直接赋值 sys.stdout；MicroPython 的 sys.stdout 只读，
    必须用 os.dupterm(io.IOBase实例, 0) 接管。
    """

    def __init__(self, max_lines=MAX_LINES):
        self.buffer = []
        self.max_lines = max_lines
        self._pending = ''
        self._subscriber = None
        self._mirror = None

    def attach(self):
        if _mp_supports_dupterm(self):
            # MicroPython：接管终端(含 print)，旧流存 _mirror 用于回显。
            # dupterm 会立即向对象调用 write，内部用原始缓冲区回显即可。
            self._mirror = None
            return self
        # CPython
        try:
            self._mirror = sys.stdout
            sys.stdout = self
            sys.stderr = self
        except Exception:
            self._mirror = None
        return self

    def on_line(self, cb):
        self._subscriber = cb

    def history(self):
        return list(self.buffer)

    def clear(self):
        self.buffer = []
        self._pending = ''

    def write(self, s):
        if self._mirror is not None:
            try:
                self._mirror.write(s)
            except Exception:
                self._mirror = None
        if not isinstance(s, str):
            try:
                s = s.decode('utf-8', 'replace')
            except Exception:
                s = str(s)
        self._pending += s
        while True:
            idx = self._pending.find('\n')
            if idx < 0:
                break
            line = self._pending[:idx]
            self._pending = self._pending[idx + 1:]
            if line.endswith('\r'):
                line = line[:-1]
            self._push(line)

    def flush(self):
        if self._pending:
            self._push(self._pending)
            self._pending = ''

    # MicroPython dupterm 需要的流接口
    def read(self, n=-1):
        return b''

    def readinto(self, buf):
        return 0

    def any(self):
        return 0

    def close(self):
        pass

    def _push(self, line):
        self.buffer.append(line)
        if len(self.buffer) > self.max_lines:
            del self.buffer[: len(self.buffer) - self.max_lines]
        if self._subscriber is not None:
            try:
                self._subscriber(line)
            except Exception:
                pass


def _mp_supports_dupterm(console):
    """MicroPython(v1.28) 下用 os.dupterm 接管终端输出。"""
    if os is None or not hasattr(os, 'dupterm'):
        return False
    if io is None or not hasattr(io, 'IOBase'):
        return False
    if not isinstance(console, io.IOBase):
        return False
    try:
        os.dupterm(console, 0)
        return True
    except Exception:
        return False


_console = None


def get_console():
    global _console
    if _console is None:
        _console = Console()
    return _console


def announce(msg):
    get_console()._push(str(msg))