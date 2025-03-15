from loguru import logger
import tomllib  # 确保导入tomllib以读取配置文件
import os  # 确保导入os模块

from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.plugin_base import PluginBase


class AdminTool(PluginBase):
    description = "停止服务插件"
    author = "fluidcat"
    version = "1.0.0"

    # 同步初始化
    def __init__(self):
        super().__init__()

        # 获取配置文件路径
        config_path = os.path.join(os.path.dirname(__file__), "config.toml")
        config = self.loadConfig(config_path).get("admintool", {})
        # 读取基本配置
        self.enable = config.get("enable", False)  # 读取插件开关

        sys_config = self.loadConfig("main_config.toml").get('XYBot')


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
        await bot.send_reply_message(message, "我已经停止处理消息")
        return False

    @on_at_message(priority=50)
    async def handle_at(self, bot: WechatAPIClient, message: dict):
        return await self.handle_text(bot, message)
