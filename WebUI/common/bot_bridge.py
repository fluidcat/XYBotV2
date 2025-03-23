import asyncio
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

from loguru import logger

from WebUI.utils.singleton import Singleton
# 引入键值数据库
from database.keyvalDB import KeyvalDB
from utils.plugin_manager import PluginManager

# 确保可以导入根目录模块
ROOT_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, str(ROOT_DIR))

# 键值数据库键名常量
KEY_MESSAGE_COUNT = "bot:stats:message_count"
KEY_USER_COUNT = "bot:stats:user_count"
KEY_LOG_POSITION = "bot:logs:last_position"


def get_or_create_eventloop():
    """
    获取当前线程的事件循环，如果不存在则创建一个新的

    返回:
        asyncio.AbstractEventLoop: 事件循环对象
    """
    try:
        # 尝试获取当前线程的事件循环
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # 如果当前线程没有事件循环，则创建一个新的
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop


class BotBridge(metaclass=Singleton):
    def __init__(self):
        # 个人资料数据
        self.avatar_url = ""
        self.nickname = ""
        self.wxid = ""
        self.alias = ""
        self.is_running = False
        self.start_time = float(0)

        # 缓存数据
        self._cache = {}
        self._cache_time = 0
        self._cache_ttl = 5  # 缓存有效期（秒）

        # 存储正在运行的任务
        self._tasks = []

        # 初始化插件管理器
        self.plugin_manager = PluginManager()

        # 配置目录
        self.config_dir = ROOT_DIR / 'plugins'

        # 初始化数据库
        self._db = KeyvalDB()

        # 异步初始化数据库
        loop = get_or_create_eventloop()
        loop.run_until_complete(self._db.initialize())

    async def get_message_count(self):
        """
        获取接收消息数量
        """
        try:
            result = await self._db.get(KEY_MESSAGE_COUNT)
            count = int(result) if result is not None else 0

            return count
        except Exception as e:
            logger.log('WEBUI', f"获取消息计数失败: {str(e)}")
            return 0

    async def increment_message_count(self, amount=1):
        """
        增加消息计数
        """
        try:
            current = await self.get_message_count()
            new_count = current + amount
            await self._db.set(KEY_MESSAGE_COUNT, str(new_count))

            return True
        except Exception as e:
            logger.log('WEBUI', f"增加消息计数失败: {str(e)}")
            return False

    async def get_user_count(self):
        """
        获取用户数量
        """
        try:
            result = await self._db.get(KEY_USER_COUNT)
            count = int(result) if result is not None else 0

            return count
        except Exception as e:
            logger.log('WEBUI', f"获取用户计数失败: {str(e)}")
            return 0

    async def increment_user_count(self, amount=1):
        """
        增加用户计数
        """
        try:
            current = await self.get_user_count()
            new_count = current + amount
            await self._db.set(KEY_USER_COUNT, str(new_count))

            return True
        except Exception as e:
            logger.log('WEBUI', f"增加用户计数失败: {str(e)}")
            return False

    async def get_start_time(self):
        """
        获取机器人启动时间
        """
        try:
            return self.start_time
        except Exception as e:
            logger.log('WEBUI', f"获取启动时间失败: {str(e)}")
            return 0

    async def save_log_position(self, position):
        """
        保存日志读取位置到数据库
        """
        try:
            await self._db.set(KEY_LOG_POSITION, str(position))
            return True
        except Exception as e:
            logger.log('WEBUI', f"保存日志位置失败: {str(e)}")
            return False

    async def get_log_position(self):
        """
        获取日志读取位置
        """
        try:
            pos = await self._db.get(KEY_LOG_POSITION)
            return int(pos) if pos is not None else 0
        except Exception as e:
            logger.log('WEBUI', f"获取日志位置失败: {str(e)}")
            return 0

    def save_profile(self, avatar_url: str = "", nickname: str = "", wxid: str = "", alias: str = ""):
        """保存个人资料信息"""
        self.avatar_url = avatar_url
        self.nickname = nickname
        self.wxid = wxid
        self.alias = alias

    def get_profile(self):
        """获取个人资料信息"""
        if self.is_running:
            return {
                "avatar": self.avatar_url,  # 注意这里改为avatar以匹配前端期望
                "nickname": self.nickname,
                "wxid": self.wxid,
                "alias": self.alias
            }
        else:
            return {
                "avatar": "",
                "nickname": "",
                "wxid": "",
                "alias": ""
            }

    def _create_task(self, coro):
        loop = get_or_create_eventloop()
        task = loop.create_task(coro)
        self._tasks.append(task)

        # 添加完成回调，完成后从列表移除
        def _done_callback(t):
            if t in self._tasks:
                self._tasks.remove(t)

            # 检查是否有异常
            if t.exception() is not None:
                logger.log('WEBUI', f"任务执行异常: {t.exception()}")

        task.add_done_callback(_done_callback)
        return task

    def get_all_plugins(self) -> List[Dict[str, Any]]:
        """
        获取所有插件信息
        
        返回:
            List[Dict[str, Any]]: 插件信息列表
        """
        try:
            # 使用同步方式执行异步操作，避免coroutine未等待问题
            loop = get_or_create_eventloop()
            if loop.is_running():
                # 如果循环正在运行，可能是在事件循环内调用，创建任务
                refresh_task = self._create_task(self.plugin_manager.refresh_plugins())
                # 但注意这种情况下，操作可能尚未完成
            else:
                # 否则阻塞等待完成
                loop.run_until_complete(self.plugin_manager.refresh_plugins())

            plugins = self.plugin_manager.get_plugin_info()

            # 格式化插件信息
            formatted_plugins = []
            for plugin in plugins:
                directory = plugin.get("directory", "unknown")
                try:
                    dir_path = ROOT_DIR / 'plugins' / directory
                    rel_path = dir_path.relative_to(ROOT_DIR).as_posix()
                except (ValueError, TypeError):
                    rel_path = directory

                formatted_plugin = {
                    "name": plugin["name"],
                    "description": plugin["description"],
                    "author": plugin["author"],
                    "version": plugin["version"],
                    "enabled": plugin["enabled"],
                    "directory": rel_path
                }
                formatted_plugins.append(formatted_plugin)

            return formatted_plugins
        except Exception as e:
            logger.log('WEBUI', f"获取插件信息出错: {str(e)}")
            return []

    def get_plugin_details(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """获取指定插件的详细信息"""
        try:
            plugin_info = self.plugin_manager.get_plugin_info(plugin_name)
            if not plugin_info:
                return None

            # 获取相对路径
            directory = plugin_info.get("directory", "unknown")
            try:
                dir_path = ROOT_DIR / 'plugins' / directory
                rel_path = dir_path.relative_to(ROOT_DIR).as_posix()
            except (ValueError, TypeError):
                rel_path = directory

            return {
                "name": plugin_info["name"],
                "description": plugin_info["description"],
                "author": plugin_info["author"],
                "version": plugin_info["version"],
                "enabled": plugin_info["enabled"],
                "directory": rel_path
            }
        except Exception as e:
            logger.log('WEBUI', f"获取插件详情出错: {str(e)}")
            return None

    async def enable_plugin(self, plugin_name: str) -> bool:
        """启用插件"""
        if not self.is_running:
            raise Exception("机器人未运行")
        try:
            return await self.plugin_manager.load_plugin(plugin_name)
        except Exception as e:
            logger.log('WEBUI', f"启用插件出错: {str(e)}")
            return False

    async def disable_plugin(self, plugin_name: str) -> bool:
        """禁用插件"""
        if not self.is_running:
            raise Exception("机器人未运行")
        try:
            return await self.plugin_manager.unload_plugin(plugin_name)
        except Exception as e:
            logger.log('WEBUI', f"禁用插件出错: {str(e)}")
            return False

    async def reload_plugin(self, plugin_name: str) -> bool:
        """重新加载插件"""
        try:
            return await self.plugin_manager.reload_plugin(plugin_name)
        except Exception as e:
            logger.log('WEBUI', f"重载插件出错: {str(e)}")
            return False


# 创建全局实例
bot_bridge = BotBridge()
