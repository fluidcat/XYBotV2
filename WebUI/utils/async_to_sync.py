import asyncio
import threading
from functools import wraps

_thread_local = threading.local()


def async_to_sync(func):
    """将异步函数转换为同步函数的装饰器，支持多线程环境"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        # 获取或创建当前线程的事件循环
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # 如果当前线程没有事件循环，创建一个新的
            if not hasattr(_thread_local, 'loop'):
                _thread_local.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(_thread_local.loop)
            loop = _thread_local.loop

        # 运行协程并返回结果
        coroutine = func(*args, **kwargs)
        if loop.is_running():
            # 如果循环已经运行，创建任务
            return asyncio.create_task(coroutine)
        else:
            # 如果循环未运行，运行直到完成
            return loop.run_until_complete(coroutine)

    return wrapper
