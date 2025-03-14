from loguru import logger
import tomllib  # 确保导入tomllib以读取配置文件
import os  # 确保导入os模块

import requests
from WechatAPI import WechatAPIClient
from utils.const import *
from utils.decorators import *
from utils.plugin_base import PluginBase


class BalancePlugin(PluginBase):
    description = "余额插件"
    author = "fluidcat"
    version = "1.0.0"

    # 同步初始化
    def __init__(self):
        super().__init__()

        # 获取配置文件路径
        config_path = os.path.join(os.path.dirname(__file__), "config.toml")
        config = self.loadConfig(config_path)

        # 读取基本配置
        basic_config = config.get("BalancePlugin", {})
        self.enable = basic_config.get("enable", False)  # 读取插件开关

    # 异步初始化
    async def async_init(self):
        return

    @on_text_message(priority=99)
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        cmd = message.get('command', '')
        if not cmd.strip().removeprefix('#') in ['系统余额', '接口额度']:
            return PLUGIN_PASS
        reply_text = ''
        reply_text += 'deepseek: ' + self.get_deepseek() + '\n'

        await bot.send_reply_message(message, reply_text)
        return PLUGIN_ENDED

    def get_deepseek(self):
        url = "https://api.deepseek.com/user/balance"

        payload = {}
        headers = {
            'Accept': 'application/json',
            'Authorization': 'Bearer sk-06d0a379dca4444dbd7c497d8cb6bec8'
        }

        resp = requests.request("GET", url, headers=headers, data=payload).json()
        infos = resp.get('balance_infos', [])
        if not infos:
            return None

        return infos[0]['total_balance']

    @on_at_message(priority=50)
    async def handle_at(self, bot: WechatAPIClient, message: dict):
        return self.handle_text(bot, message)

    @on_voice_message()
    async def handle_voice(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return
        logger.info("收到了语音消息，最低优先级")

    @on_image_message
    async def handle_image(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return
        logger.info("收到了图片消息")

    @on_video_message
    async def handle_video(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return
        logger.info("收到了视频消息")

    @on_file_message
    async def handle_file(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return
        logger.info("收到了文件消息")

    @on_quote_message
    async def handle_quote(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return
        logger.info("收到了引用消息")

    @on_pat_message
    async def handle_pat(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return
        logger.info("收到了拍一拍消息")

    @on_emoji_message
    async def handle_emoji(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return
        logger.info("收到了表情消息")


