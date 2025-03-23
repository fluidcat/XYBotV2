import asyncio
import os
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Optional, Dict, Any, Union

from loguru import logger

from WebUI.common.bot_bridge import bot_bridge
from WebUI.utils.singleton import Singleton

# 项目根目录路径
ROOT_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 导入机器人主函数
sys.path.append(str(ROOT_DIR))
from bot import run_bot

# 线程本地存储，用于存储每个线程的事件循环
thread_local = threading.local()


def get_or_create_eventloop() -> asyncio.AbstractEventLoop:
    try:
        # 尝试获取当前线程的事件循环
        loop = asyncio.get_event_loop()
        # 检查事件循环是否已关闭，已关闭则创建新循环
        if loop.is_closed():
            logger.log('WEBUI', f"检测到线程 {threading.current_thread().name} 的事件循环已关闭，创建新循环")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        # 如果当前线程没有事件循环，则创建一个新的
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        logger.log('WEBUI', f"为线程 {threading.current_thread().name} 创建了新的事件循环")

    return loop


class BotService(metaclass=Singleton):
    def __init__(self):
        """初始化机器人控制服务
        
        设置内部状态变量，用于跟踪机器人运行状态。
        """
        self._task: Optional[Union[asyncio.Task, asyncio.Future]] = None
        self._start_time: float = 0
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._bot_thread: Optional[threading.Thread] = None
        logger.log('WEBUI', "机器人服务初始化完成")

    def start_bot(self) -> bool:
        """启动机器人
        
        创建并运行机器人主协程，根据当前事件循环状态选择合适的启动方式。
        如果事件循环未运行，会在新线程中启动事件循环。
        
        Returns:
            bool: 启动是否成功
        """
        # 如果机器人已在运行，直接返回
        if self.is_running():
            logger.log('WEBUI', "机器人已经在运行中，无需重复启动")
            return True

        try:
            # 获取或创建事件循环
            loop = get_or_create_eventloop()
            self._loop = loop
            logger.log('WEBUI', "准备启动机器人...")

            # 在事件循环中创建并运行任务
            if loop.is_running():
                # 如果循环已经在运行，使用asyncio.run_coroutine_threadsafe
                logger.log('WEBUI', "在现有事件循环中启动机器人")
                future = asyncio.run_coroutine_threadsafe(run_bot(), loop)
                self._task = future
            else:
                # 如果循环未运行，在新线程中运行事件循环
                logger.log('WEBUI', "创建新的事件循环来启动机器人")
                self._task = loop.create_task(run_bot())

                # 在单独的线程中运行事件循环
                def run_loop():
                    try:
                        logger.log('WEBUI', "事件循环开始运行")
                        loop.run_forever()
                    except Exception as e:
                        logger.log('WEBUI', f"事件循环异常: {str(e)}")
                        logger.log('WEBUI', traceback.format_exc())
                    finally:
                        logger.log('WEBUI', "事件循环已关闭")

                self._bot_thread = threading.Thread(target=run_loop, daemon=True)
                self._bot_thread.start()
                logger.log('WEBUI', f"已在后台线程启动事件循环 (线程ID: {self._bot_thread.ident})")

            self._start_time = time.time()
            bot_bridge.start_time = self._start_time
            bot_bridge.is_running = True
            logger.log('WEBUI', "机器人启动成功")

            return True
        except Exception as e:
            logger.log('WEBUI', f"启动机器人失败: {str(e)}")
            logger.log('WEBUI', traceback.format_exc())
            return False

    def stop_bot(self) -> bool:
        """停止机器人
        
        取消正在运行的机器人任务，并根据需要停止事件循环。
        清理相关资源并重置状态。
        
        Returns:
            bool: 停止是否成功
        """
        if not self.is_running():
            logger.log('WEBUI', "机器人未在运行，无需停止")
            return True

        try:
            logger.log('WEBUI', "开始停止机器人...")

            # 取消异步任务
            if self._task:
                if isinstance(self._task, asyncio.Task) and not self._task.done():
                    logger.log('WEBUI', "取消机器人任务")
                    self._task.cancel()
                elif hasattr(self._task, 'cancel'):
                    logger.log('WEBUI', "取消机器人Future")
                    self._task.cancel()

            # 停止事件循环
            if self._loop and not self._loop.is_closed() and self._loop.is_running():
                logger.log('WEBUI', "停止事件循环")
                self._loop.call_soon_threadsafe(self._loop.stop)

            # 重置状态
            self._task = None
            self._start_time = 0
            self._bot_thread = None 
            self._loop = None
            bot_bridge.start_time = 0
            bot_bridge.is_running = False
            logger.log('WEBUI', "机器人已成功停止")

            return True
        except Exception as e:
            logger.log('WEBUI', f"停止机器人失败: {str(e)}")
            logger.log('WEBUI', traceback.format_exc())
            return False

    def is_running(self) -> bool:
        """检查机器人是否正在运行
        
        通过检查异步任务的状态确定机器人是否在运行。
        如果任务已完成或出错，会重置状态。
        
        Returns:
            bool: 机器人是否正在运行
        """
        # 检查异步任务是否正在运行
        if self._task:
            if isinstance(self._task, asyncio.Task) and not self._task.done():
                return True
            elif hasattr(self._task, 'done') and not self._task.done():
                return True

        # 如果任务已完成或出错，重置状态
        if self._task is not None:
            logger.log('WEBUI', "检测到机器人任务已完成或出错，重置状态")
            self._task = None
            self._start_time = 0
            self._loop = None
            self._bot_thread = None
            bot_bridge.start_time = 0
            bot_bridge.is_running = False

        return False

    def get_status(self) -> Dict[str, Any]:
        """获取机器人状态信息
        
        收集当前运行状态、进程ID和启动时间等信息。
        
        Returns:
            Dict[str, Any]: 包含状态信息的字典
        """
        running = self.is_running()

        status = {
            'running': running,
            'pid': os.getpid(),
            'start_time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self._start_time)) if running else 0,
        }

        return status


# 创建机器人控制服务实例
bot_service = BotService()
