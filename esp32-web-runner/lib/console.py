import sys

MAX_LINES = 500


class Console:
    """全局控制台：接管 sys.stdout/stderr，缓存最近日志并转发给订阅者(WebSocket)。"""

    def __init__(self, max_lines=MAX_LINES):
        self.buffer = []
        self.max_lines = max_lines
        self._pending = ''
        self._subscriber = None
        self._mirror = None

    def attach(self):
        self._mirror = sys.stdout
        sys.stdout = self
        sys.stderr = self
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

    def _push(self, line):
        self.buffer.append(line)
        if len(self.buffer) > self.max_lines:
            del self.buffer[: len(self.buffer) - self.max_lines]
        if self._subscriber is not None:
            try:
                self._subscriber(line)
            except Exception:
                pass


_console = None


def get_console():
    global _console
    if _console is None:
        _console = Console()
    return _console


def announce(msg):
    get_console()._push(str(msg))