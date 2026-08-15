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

# MicroPython 端 USB-Serial/JTAG 的 TX FIFO 很小（约 256B）。无主机读串口时
# （headless 使用，比如只插 USB 供电后直接 curl 测试），FIFO 一旦写满，
# sys.stdout.write() 会永久阻塞，而 MicroPython 单线程 —— 事件循环随之停摆，
# 入站连接全废（出站也废）。这是 S3(全速 USB 大缓冲) 能跑、C3 跑不起来的根因。
# 对策：C3 上串口日志设严格字节预算，预算耗尽后只进网页控制台，绝不阻塞主循环。
_MP_SERIAL_BUDGET = 192


def _on_mp():
    try:
        return getattr(sys.implementation, 'name', '') == 'micropython'
    except Exception:
        return False


class Console(io.IOBase if (io and hasattr(io, 'IOBase')) else object):
    """全局控制台：接管 print 输出，缓存最近日志并转发给订阅者(WebSocket)。

    平台差异：CPython 直接赋值 sys.stdout；MicroPython 不碰 sys.stdout/sys.stdin
    （保护 REPL 与 mpremote），改为打补丁 builtins.print，让所有 print 同时
    进入控制台缓冲并转发给网页订阅者。串口原样可见（print 仍调原实现 /
    _push 直写 sys.stdout）。
    """

    def __init__(self, max_lines=MAX_LINES):
        self.buffer = []
        self.max_lines = max_lines
        self._pending = ''
        self._subscriber = None
        self._mirror = None
        self._serial = None
        self._orig_print = None
        self._serial_budget = _MP_SERIAL_BUDGET if _on_mp() else None
        try:
            self._serial = sys.stdout
        except Exception:
            self._serial = None

    def attach(self):
        # 先把真实 stdout 记下来（CPython 后面会被替换，_push 的串口输出用）
        try:
            self._serial = sys.stdout
        except Exception:
            self._serial = None
        if _mp_can_patch_print(self):
            # MicroPython：不用 os.dupterm。dupterm 是"单流双向"，一旦接管，
            # 输入也一起吞掉，Ctrl-C / mpremote / raw REPL 全部失效。
            # 改为打补丁 builtins.print：所有 print 同时进控制台缓冲 + 串口，
            # sys.stdout/sys.stdin 保持原样，REPL 与 mpremote 100% 可用。
            try:
                import builtins
            except ImportError:
                builtins = None
            if builtins is not None and hasattr(builtins, 'print'):
                try:
                    self._orig_print = builtins.print

                    def _cap(*args, **kwargs):
                        # 单一路径：console 缓冲 + 预算化串口写（都在 _push 里）。
                        # 不再调 _orig_print —— 否则每行 print 串口写两遍，
                        # 启动十几行（近 400B）就能撑爆 C3 的 USB-Serial/JTAG
                        # 小 FIFO 而阻塞主循环。
                        try:
                            self.write(' '.join(str(a) for a in args) + '\n')
                        except Exception:
                            pass

                    builtins.print = _cap
                except Exception:
                    pass
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

    def close(self):
        pass

    def _mp_serial_writable(self):
        """MicroPython：探测 stdout（USB-CDC）当前是否可写。

        headless（无主机读串口）时 USB-Serial/JTAG 的 TX FIFO 会写满，
        同步 write() 可能把单线程主循环永久堵死。用 select 做 0 超时探测：
        可写返回 True，不可写返回 False（直接跳过串口写，日志仍进网页
        控制台）。若该 stream 不支持 poll（select 抛异常），回退为"视为
        可写"（保持旧行为），零风险。
        """
        try:
            import select
            _, w, _ = select.select([], [self._serial], [], 0)
            return bool(w)
        except Exception:
            return True

    def _push(self, line):
        self.buffer.append(line)
        if len(self.buffer) > self.max_lines:
            del self.buffer[: len(self.buffer) - self.max_lines]
        if self._serial is not None:
            if self._serial_budget is not None:
                # MicroPython：预算化 + 可写探测双保险。预算按字节递减，
                # 耗尽后永久静默（日志仍进网页控制台缓冲）。写前先探测
                # stdout 是否可写，headless 下 FIFO 满时跳过本轮串口写，
                # 彻底避免同步 write 阻塞单线程主循环（DEBUG_NOTES 二十节）。
                need = len(line) + 1
                if need <= self._serial_budget:
                    self._serial_budget -= need
                    try:
                        if self._mp_serial_writable():
                            self._serial.write(line + '\n')
                    except Exception:
                        self._serial = None
                else:
                    self._serial = None
            else:
                try:
                    self._serial.write(line + '\n')
                except Exception:
                    self._serial = None
        if self._subscriber is not None:
            try:
                self._subscriber(line)
            except Exception:
                pass


def _mp_can_patch_print(console):
    """MicroPython 下是否可用 builtins.print 补丁捕获日志（只探测，不执行）。"""
    try:
        import builtins
    except ImportError:
        return False
    return hasattr(builtins, 'print')


_console = None


def get_console():
    global _console
    if _console is None:
        _console = Console()
    return _console


def announce(msg):
    get_console()._push(str(msg))