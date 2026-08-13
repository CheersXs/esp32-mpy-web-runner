"""用户程序(uvm)辅助库：程序内 `import uvm` 即可使用。

约定：
- 异步程序必须定义 `async def main():`，循环里用 `await uvm.sleep_ms(n)`。
- 同步脚本直接从上到下执行，用 `uvm.sleep_ms(n)` 延时（线程内阻塞式）。
- `uvm.should_stop()` 检查是否收到"停止"信号，建议长循环里定期调用。
- 第一行注释可强制类型：#type:async  /  #type:sync
"""

import time as _time

_stop_flags = {}
# 当前程序名按"线程/任务"隔离，避免多程序并发时 should_stop() 串扰。
# key: ('t', thread_id) 同步线程  /  ('a', id(task)) 异步任务  /  ('m', 0) 主线程
_current = {}


def _ctx_key():
    try:
        import _thread
        return ('t', _thread.get_ident())
    except Exception:
        pass
    try:
        import asyncio
        t = asyncio.current_task()
        if t is not None:
            return ('a', id(t))
    except Exception:
        pass
    return ('m', 0)


def _set_current(name):
    if name is None:
        _current.pop(_ctx_key(), None)
    else:
        _current[_ctx_key()] = name


def _set_stop(name, value):
    _stop_flags[name] = bool(value)


def should_stop():
    name = _current.get(_ctx_key())
    if name is None:
        return False
    return _stop_flags.get(name, False)


def sleep_ms(ms):
    """延时：协程里返回 awaitable（await uvm.sleep_ms(500)）；
    线程里直接阻塞睡眠。兼容 MicroPython 与 PC(CPython)。"""
    try:
        import asyncio
        if asyncio.current_task() is not None:
            # 在协程里
            if hasattr(asyncio, 'sleep_ms'):
                return asyncio.sleep_ms(ms)       # MicroPython
            return asyncio.sleep(ms / 1000.0)     # PC
    except Exception:
        pass
    import time as _t
    if hasattr(_t, 'sleep_ms'):
        _t.sleep_ms(ms)                            # MicroPython
    else:
        _t.sleep(ms / 1000.0)                      # PC
    return None


def log(*args):
    print(*args)


registry = {}


def set(key, value):
    registry[key] = value


def get(key, default=None):
    return registry.get(key, default)