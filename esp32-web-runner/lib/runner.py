"""程序管理器：列表 / 新建 / 读取 / 保存 / 启动 / 停止 / 删除 / 重命名。

- 异步程序（#type:async 或含 async def main）在事件循环里跑成 asyncio 任务，可随时取消。
- 同步脚本（#type:sync 或普通脚本）在独立线程里跑，互不阻塞 Web 服务。
  停止 = 协作式：脚本调用 uvm.should_stop() 及时退出；顽固死循环只能靠看门狗重启兜底。
"""

import os
import sys
import gc
import time

import uvm

PROGRAMS_DIR = '/programs'
MAX_SYNC = 2

try:
    import asyncio
except ImportError:
    import uasyncio as asyncio

try:
    import _thread
except ImportError:
    _thread = None


async def _sleep_ms(ms):
    """兼容 MicroPython(uasyncio.sleep_ms) 与 CPython(asyncio.sleep)。"""
    if hasattr(asyncio, 'sleep_ms'):
        await asyncio.sleep_ms(ms)
    else:
        await asyncio.sleep(ms / 1000.0)


class Program:
    def __init__(self, name):
        self.name = name
        self.path = PROGRAMS_DIR + '/' + name + '.py'
        self.type = 'sync'
        self.status = 'stopped'   # stopped | running | error
        self.error = ''
        self.task = None


def _safe_name(name):
    if not name:
        return ''
    ok = all(c.isalnum() or c == '_' for c in name)
    if not ok:
        return ''
    if name.startswith('_'):
        return ''
    if len(name) > 40:
        return ''
    return name


class Manager:
    def __init__(self, console):
        self.console = console
        self.programs = {}
        self._sync_count = 0
        self.spawn_dir()
        sys.path.append(PROGRAMS_DIR)

    def spawn_dir(self):
        try:
            if PROGRAMS_DIR not in os.listdir('/'):
                os.mkdir(PROGRAMS_DIR)
        except Exception:
            pass

    # ---------- 文件操作 ----------

    def list_programs(self):
        names = []
        cur = {n: None for n in self.programs}
        try:
            entries = os.listdir(PROGRAMS_DIR)
        except OSError:
            entries = []
        for e in entries:
            if e.endswith('.py') and not e.startswith('.'):
                names.append(e[:-3])
        names.sort()
        remove = []
        for nm in cur:
            if nm not in names:
                remove.append(nm)
        for nm in remove:
            p = self.programs.pop(nm)
            if p.task is not None:
                try:
                    p.task.cancel()
                    uvm._set_stop(nm, True)
                except Exception:
                    pass
        return names

    def get_program(self, name):
        p = self.programs.get(name)
        if p is None:
            p = Program(name)
        return p

    def read_code(self, name):
        p = self.get_program(name)
        with open(p.path, 'r') as f:
            return f.read()

    def save_code(self, name, code):
        p = self.get_program(name)
        if p.status == 'running':
            raise RuntimeError('程序正在运行，请先停止再保存')
        if not isinstance(code, str):
            raise RuntimeError('代码内容必须是文本')
        try:
            compile(code, name + '.py', 'exec')
        except Exception as e:
            raise RuntimeError('语法错误：%s' % e)
        with open(p.path, 'w') as f:
            f.write(code)
        p.type = self._resolve_type(code)
        p.error = ''
        return p

    def create_program(self, name, code):
        nm = _safe_name(name)
        if not nm:
            raise RuntimeError('文件名只能包含字母/数字/下划线')
        p = self.get_program(nm)
        try:
            f = open(p.path, 'r')
            f.close()
            raise RuntimeError('已存在同名程序')
        except OSError:
            pass
        self.save_code(nm, code)
        return nm

    def delete_program(self, name):
        p = self.get_program(name)
        if p.status == 'running':
            raise RuntimeError('程序正在运行，请先停止再删除')
        try:
            os.remove(p.path)
        except OSError:
            raise RuntimeError('文件不存在')
        self.programs.pop(name, None)

    def rename_program(self, name, new_name):
        nm = _safe_name(new_name)
        if not nm:
            raise RuntimeError('新文件名只能包含字母/数字/下划线')
        p = self.get_program(name)
        if p.status == 'running':
            raise RuntimeError('程序正在运行，请先停止再重命名')
        if nm == name:
            return nm
        new_path = PROGRAMS_DIR + '/' + nm + '.py'
        try:
            os.rename(p.path, new_path)
        except OSError:
            raise RuntimeError('重命名失败（目标可能已存在）')
        self.programs.pop(name, None)
        return nm

    @staticmethod
    def _resolve_type(code):
        text = (code or '').lstrip()
        if text:
            first = text.split('\n', 1)[0].strip().lower()
            if first.startswith('#'):
                if 'async' in first:
                    return 'async'
                if 'sync' in first:
                    return 'sync'
        if 'async def main' in text:
            return 'async'
        return 'sync'

    def _announce(self, msg):
        if self.console:
            try:
                self.console._push(msg)
            except Exception:
                pass

    # ---------- 运行控制 ----------

    def start(self, name):
        p = self.programs.get(name)
        if p is not None and (p.task is not None or p.status == 'running'):
            raise RuntimeError('程序已在运行')
        code = self.read_code(name)
        p = self.get_program(name)
        self.programs[name] = p
        p.type = self._resolve_type(code)
        p.error = ''
        if p.type == 'async':
            try:
                compile(code, name + '.py', 'exec')
            except Exception as e:
                raise RuntimeError('语法错误：%s' % e)
            p.status = 'running'
            p.task = asyncio.create_task(self._run_async(p, code))
        else:
            if _thread is None:
                raise RuntimeError('当前固件不支持多线程，无法运行同步脚本')
            if self._sync_count >= MAX_SYNC:
                raise RuntimeError('同步程序并发数已达上限(%d)' % MAX_SYNC)
            p.status = 'running'
            self._sync_count += 1
            try:
                _thread.start_new_thread(self._run_sync, (p, code))
            except Exception as e:
                self._sync_count -= 1
                p.status = 'stopped'
                raise RuntimeError('线程创建失败：%s' % e)
        self._announce('[%s] 已启动 (%s)' % (name, p.type))
        return p

    async def _run_async(self, p, code):
        ns = {'__name__': '__main__'}
        ctx_key = uvm._set_current(p.name)
        uvm._set_stop(p.name, False)
        try:
            gc.collect()
            exec(compile(code, p.name + '.py', 'exec'), ns)
            main = ns.get('main')
            if main is None:
                raise NameError('异步程序必须定义 async def main()')
            await main()
            p.status = 'stopped'
            self._announce('[%s] 正常结束' % p.name)
        except asyncio.CancelledError:
            p.status = 'stopped'
            self._announce('[%s] 已停止' % p.name)
        except Exception as e:
            p.status = 'error'
            p.error = _fmt_error(e)
            self._announce('[%s] 出错：%s' % (p.name, p.error))
            try:
                sys.print_exception(e)
            except Exception:
                pass
        finally:
            p.task = None
            uvm._clear_current(ctx_key)

    def _run_sync(self, p, code):
        ns = {'__name__': '__main__'}
        ctx_key = uvm._set_current(p.name)
        uvm._set_stop(p.name, False)
        try:
            gc.collect()
            exec(compile(code, p.name + '.py', 'exec'), ns)
            if p.status == 'running':
                p.status = 'stopped'
            self._announce('[%s] 正常结束' % p.name)
        except SystemExit:
            p.status = 'stopped'
        except Exception as e:
            p.status = 'error'
            p.error = _fmt_error(e)
            self._announce('[%s] 出错：%s' % (p.name, p.error))
            try:
                sys.print_exception(e, sys.stdout)
            except Exception:
                pass
        finally:
            if p.status == 'running':
                p.status = 'stopped'
            uvm._clear_current(ctx_key)
            self._sync_count = max(0, self._sync_count - 1)

    def stop(self, name):
        p = self.get_program(name)
        if p.status == 'stopped' and p.task is None:
            raise RuntimeError('程序没有在运行')
        if p.task is not None:
            task = p.task
            try:
                if task.done():
                    # 任务已结束但状态未清理（协程体未执行就被取消等），手动收尾
                    p.task = None
                    p.status = 'stopped'
                    raise RuntimeError('程序没有在运行')
            except RuntimeError:
                raise
            except Exception:
                pass
            try:
                task.cancel()
            except Exception:
                task = None
            uvm._set_stop(name, True)
            if task is not None:
                # cancel 一个尚未开始运行(pending)的任务时，协程体不会执行，
                # _run_async 的 finally 也就不会清理状态，任务会在事件循环
                # 下一 tick 变成 done。这里注册一个回调及时收尾，避免
                # status 卡在 running / task 指向已取消任务。
                def _finalize_cancelled(t=task):
                    try:
                        if t.done():
                            cur = self.programs.get(name)
                            if cur is not None and cur.task is t:
                                cur.task = None
                                if cur.status == 'running':
                                    cur.status = 'stopped'
                    except Exception:
                        pass
                try:
                    asyncio.get_event_loop().call_soon(_finalize_cancelled)
                except Exception:
                    _finalize_cancelled()
            self._announce('[%s] 发送停止信号...' % name)
        else:
            uvm._set_stop(name, True)
            self._announce('[%s] 请求停止 (等待程序响应)' % name)

    async def restart(self, name, code=None):
        """重启程序；若传入 code 则先保存再启动（用于"保存并重启"）。"""
        try:
            self.stop(name)
        except RuntimeError:
            pass
        # 轮询等待程序真正停止（异步任务取消后 finally 才置 stopped），
        # 避免固定延时不够导致 start() 报"程序已在运行"。
        #
        # 注意：若任务在 pending（尚未开始执行）时被 cancel，协程体不会运行，
        # _run_async 的 finally 也不会清理状态，任务会直接变成 done。
        # 此时需手动收尾，否则 status 会一直卡在 running。
        for _ in range(50):
            p = self.get_program(name)
            if p.task is not None:
                try:
                    if p.task.done():
                        p.task = None
                        p.status = 'stopped'
                except Exception:
                    pass
            if p.status == 'stopped' and p.task is None:
                break
            await _sleep_ms(50)
        if code is not None:
            self.save_code(name, code)
        return self.start(name)

    # ---------- 状态 ----------

    def status_snapshot(self):
        out = []
        for nm in self.list_programs():
            p = self.programs.get(nm)
            if p is None:
                try:
                    code = self.read_code(nm)
                except Exception:
                    code = ''
                typ = self._resolve_type(code)
                out.append({'name': nm, 'type': typ, 'status': 'stopped', 'error': ''})
            else:
                out.append({'name': nm, 'type': p.type, 'status': p.status,
                            'error': p.error})
        return out

    def is_running(self, name):
        p = self.programs.get(name)
        return p is not None and p.status == 'running'

    def autostart(self, names):
        for nm in names:
            try:
                self.start(nm)
                self._announce('[boot] 自动启动 %s' % nm)
            except Exception as e:
                self._announce('[boot] 自动启动 %s 失败：%s' % (nm, e))


def _fmt_error(e):
    st = str(e).strip()
    if not st:
        st = e.__class__.__name__
    return st[:300]