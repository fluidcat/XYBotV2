from loguru import logger
import tomllib  # 确保导入tomllib以读取配置文件
import os  # 确保导入os模块

from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.plugin_base import PluginBase


class StopService(PluginBase):
    description = "停止服务插件"
    author = "fluidcat"
    version = "1.0.0"

    # 同步初始化
    def __init__(self):
        super().__init__()

        # 获取配置文件路径
        config_path = os.path.join(os.path.dirname(__file__), "config.toml")
        
        try:
            with open(config_path, "rb") as f:
                config = tomllib.load(f)
                
            # 读取基本配置
            basic_config = config.get("basic", {})
            self.enable = basic_config.get("enable", False)  # 读取插件开关

        except Exception as e:
            logger.error(f"加载ExamplePlugin配置文件失败: {str(e)}")
            self.enable = False  # 如果加载失败，禁用插件

    # 异步初始化
    async def async_init(self):
        return

    @on_text_message(priority=55)
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        cmd = message.get("command", "")
        if not cmd.startswith("#") or cmd != '#停止响应':
            return
        bot.stop_sync_message = True
        logger.info("xybot 已经停止处理消息")
        return False

    @on_at_message(priority=50)
    async def handle_at(self, bot: WechatAPIClient, message: dict):
        return await self.handle_text(bot, message)
