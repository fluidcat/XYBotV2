import asyncio
import logging
import os
import time
from pathlib import Path

from WebUI.common.bot_bridge import bot_bridge
from WebUI.services.bot_service import bot_service
from WebUI.utils.async_to_sync import async_to_sync
from WebUI.utils.singleton import Singleton

# 项目根目录路径
ROOT_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
# 日志目录
LOGS_DIR = ROOT_DIR / 'logs'
# 日志文件路径
BOT_LOG_PATH = LOGS_DIR / 'xybot.log'

# 设置日志记录器
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class DataService(metaclass=Singleton):
    """数据服务类，提供机器人状态和统计数据"""

    def __init__(self):
        """初始化数据服务"""
        self._cache = {}
        self._last_update = 0
        self._update_interval = 5  # 更新间隔（秒）
        self._last_user_sync_time = 0  # 上次同步用户数量的时间
        # 确保异步初始化被执行
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(self._init_async())
        # 日志文件位置追踪
        self._log_last_position = 0

    async def _init_async(self):
        """异步初始化"""
        self._log_last_position = await bot_bridge.get_log_position()

    def get_bot_status(self):
        """
        获取机器人当前运行状态
        
        返回:
            dict: 包含状态信息的字典
        """
        # 检查缓存是否需要更新
        return {
            'running': bot_service.is_running(),
            'status': 'running' if bot_service.is_running() else 'stopped',
            'uptime': self._get_uptime(),
            'message_count': self._cache.get('messages', 0),
            'user_count': self._cache.get('users', 0)
        }

    def get_metrics(self):
        """
        获取机器人核心指标
        """
        # 先刷新缓存数据再返回
        self._refresh_cache_data()
        
        return {
            'messages': self._cache.get('messages', 0),
            'users': self._cache.get('users', 0),
            'uptime': self._get_uptime_formatted()
        }
        
    def _refresh_cache_data(self):
        """
        刷新缓存数据
        """
        current_time = time.time()
        # 如果距离上次更新时间超过了更新间隔，则更新缓存
        if current_time - self._last_update > self._update_interval:
            try:
                # 获取事件循环
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # 直接同步执行异步操作
                if loop.is_running():
                    # 如果循环正在运行，使用Future同步等待结果
                    messages = asyncio.run_coroutine_threadsafe(bot_bridge.get_message_count(), loop).result(5)
                    users = asyncio.run_coroutine_threadsafe(bot_bridge.get_user_count(), loop).result(5)
                else:
                    # 否则直接执行到完成
                    messages = loop.run_until_complete(bot_bridge.get_message_count())
                    users = loop.run_until_complete(bot_bridge.get_user_count())
                
                # 同步XYBotDB的真实用户数量到KeyvalDB (每10分钟执行一次)
                ten_minutes = 600  # 10分钟的秒数
                if current_time - self._last_user_sync_time > ten_minutes:
                    try:
                        # 导入XYBotDB以获取真实用户数量
                        from database.XYBotDB import XYBotDB
                        db = XYBotDB()
                        real_users_count = db.get_users_count()
                        
                        # 只有当实际用户数大于当前计数时才更新
                        if real_users_count > users:
                            if loop.is_running():
                                asyncio.run_coroutine_threadsafe(
                                    bot_bridge._db.set("bot:stats:user_count", str(real_users_count)), 
                                    loop
                                ).result(5)
                                users = real_users_count
                            else:
                                loop.run_until_complete(
                                    bot_bridge._db.set("bot:stats:user_count", str(real_users_count))
                                )
                                users = real_users_count
                            logger.info(f"已从XYBotDB同步用户数量: {real_users_count}")
                        
                        self._last_user_sync_time = current_time
                    except Exception as e:
                        logger.error(f"同步用户数量失败: {str(e)}")
                
                # 更新缓存 - 直接从bot_bridge获取start_time，不需要异步调用
                self._cache['messages'] = messages
                self._cache['users'] = users
                self._cache['start_time'] = bot_bridge.start_time
                self._last_update = current_time
                logger.info(f"缓存数据已刷新: 消息数={messages}, 用户数={users}, 启动时间={bot_bridge.start_time}")
            except Exception as e:
                logger.error(f"刷新缓存数据失败: {str(e)}")
                # 使用默认值
                self._cache.setdefault('messages', 0)
                self._cache.setdefault('users', 0)
                self._cache.setdefault('start_time', 0)

    def get_recent_logs(self, n=100):
        """
        获取最近的日志
        """
        logs = []

        try:
            if BOT_LOG_PATH.exists():
                with open(BOT_LOG_PATH, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    logs = lines[-n:] if len(lines) > n else lines

                # 更新日志位置指针
                self._log_last_position = os.path.getsize(BOT_LOG_PATH)
                self._save_log_position()
        except Exception as e:
            error_msg = f"读取日志文件出错: {str(e)}"
            logger.error(error_msg)
            logs = [error_msg]

        # 确保返回的是字符串列表，并移除每行末尾的换行符
        return [line.strip() if isinstance(line, str) else str(line).strip() for line in logs]

    def get_new_logs(self):
        """
        获取新增的日志内容（增量更新）
        """
        new_logs = []

        try:
            if BOT_LOG_PATH.exists():
                current_size = os.path.getsize(BOT_LOG_PATH)

                # 检查是否有新内容
                if current_size > self._log_last_position:
                    with open(BOT_LOG_PATH, 'r', encoding='utf-8') as f:
                        # 移动到上次读取的位置
                        f.seek(self._log_last_position)
                        # 读取新增内容
                        new_lines = f.readlines()
                        new_logs = [line.strip() for line in new_lines]

                    # 更新位置指针
                    self._log_last_position = current_size
                    self._save_log_position()
        except Exception as e:
            error_msg = f"读取新增日志出错: {str(e)}"
            logger.error(error_msg)
            new_logs = [error_msg]

        # 确保返回的是字符串列表
        return [line if isinstance(line, str) else str(line) for line in new_logs]

    @async_to_sync
    async def _save_log_position(self):
        """保存日志读取位置到数据库"""
        try:
            await bot_bridge.save_log_position(self._log_last_position)
            return True
        except Exception as e:
            logger.error(f"保存日志位置失败: {str(e)}")
            return False

    @async_to_sync
    async def _get_message_count(self):
        """
        获取接收消息数量
        """
        try:
            return await bot_bridge.get_message_count()
        except Exception as e:
            logger.error(f"获取消息计数失败: {str(e)}")
            return 0

    @async_to_sync
    async def _get_user_count(self):
        """
        获取用户数量
        """
        try:
            return await bot_bridge.get_user_count()
        except Exception as e:
            logger.error(f"获取用户计数失败: {str(e)}")
            return 0

    @async_to_sync
    async def _get_start_time(self):
        """
        获取机器人启动时间
        
        返回:
            float: 启动时间戳
        """
        try:
            return await bot_bridge.get_start_time()
        except Exception as e:
            logger.error(f"获取启动时间失败: {str(e)}")
            return 0

    def _get_uptime(self):
        """
        获取机器人运行时长（秒）
        
        返回:
            int: 运行时长（秒）
        """
        try:
            if not bot_service.is_running():
                return 0

            start_time = self._cache.get('start_time', 0)
            if start_time == 0:
                return 0

            return int(time.time() - float(start_time))
        except Exception as e:
            logger.error(f"计算运行时长失败: {str(e)}")
            return 0

    def _get_uptime_formatted(self):
        """
        获取格式化的运行时长
        
        返回:
            str: 格式化的运行时长
        """
        try:
            uptime_seconds = self._get_uptime()

            if uptime_seconds == 0:
                return "未运行"

            # 将秒转换为天、小时、分钟、秒
            days, remainder = divmod(uptime_seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)

            if days > 0:
                return f"{days}天 {hours}小时"
            elif hours > 0:
                return f"{hours}小时 {minutes}分钟"
            elif minutes > 0:
                return f"{minutes}分钟 {seconds}秒"
            else:
                return f"{seconds}秒"
        except Exception as e:
            logger.error(f"格式化运行时长失败: {str(e)}")
            return "未知"

    @async_to_sync
    async def increment_message_count(self, amount=1):
        """
        增加消息计数
        
        参数:
            amount (int): 增加数量
        
        返回:
            bool: 操作是否成功
        """
        try:
            return await bot_bridge.increment_message_count(amount)
        except Exception as e:
            logger.error(f"增加消息计数失败: {str(e)}")
            return False

    @async_to_sync
    async def increment_user_count(self, amount=1):
        """
        增加用户计数
        
        参数:
            amount (int): 增加数量
        
        返回:
            bool: 操作是否成功
        """
        try:
            return await bot_bridge.increment_user_count(amount)
        except Exception as e:
            logger.error(f"增加用户计数失败: {str(e)}")
            return False


# 创建数据服务实例
data_service = DataService()
