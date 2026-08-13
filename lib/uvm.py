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
# key: ('a', id(task)) 异步任务  /  ('t', thread_id) 同步线程  /  ('m', 0) 主线程
_current = {}


def _ctx_key():
    # 注意：必须先检查 asyncio.current_task()，再检查 _thread。
    # MicroPython 的 asyncio 是单线程事件循环，所有任务跑在主线程里，
    # 若先取 _thread.get_ident() 会得到相同的主线程 ID，导致任务间 key 冲突。
    try:
        import asyncio
        t = asyncio.current_task()
        if t is not None:
            return ('a', id(t))
    except Exception:
        pass
    try:
        import _thread
        return ('t', _thread.get_ident())
    except Exception:
        pass
    return ('m', 0)


def _set_current(name):
    """设置当前上下文对应的程序名，返回上下文 key（供 _clear_current 使用）。"""
    key = _ctx_key()
    if name is None:
        _current.pop(key, None)
    else:
        _current[key] = name
    return key


def _clear_current(key):
    """用保存的 key 清除当前上下文（避免任务取消后 _ctx_key() 变化导致清不掉）。"""
    try:
        _current.pop(key, None)
    except Exception:
        pass


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