import os  # 确保导入os模块
import re

import requests
from loguru import logger

from WechatAPI import WechatAPIClient
from plugins.LLMBridge.LLMBridge_config import conf, load_config
from plugins.LLMBridge.bot.bot_factory import create_bot
from plugins.LLMBridge.bridge.bridge import Bridge
from plugins.LLMBridge.bridge.context import Context, ContextType
from plugins.LLMBridge.role import Role, RolePlay
from utils.const import *
from utils.decorators import *
from utils.plugin_base import PluginBase


class Smsforward(PluginBase):
    description = "处理短信转发插件"
    author = "fluidcat"
    version = "1.0.0"

    # 同步初始化
    def __init__(self):
        super().__init__()

        # 获取配置文件路径
        config_path = os.path.join(os.path.dirname(__file__), "config.toml")
        config = self.loadConfig(config_path).get("Smsforward", {})

        # 读取基本配置
        self.enable = config.get("enable", False)  # 读取插件开关
        self.link_icon = config.get("link_icon", '')
        self.send_to = config.get("send_to", '')

        load_config()
        open_ai_config = conf().get("open_ai_compatible").get(config.get('open_ai_compatible', 'wwxq'))

        self.api_key = open_ai_config.get('open_ai_api_key')
        self.api_base = open_ai_config.get('open_ai_api_base')
        self.model = open_ai_config.get('model')

        bot_type = Bridge().infer_bot_type(self.model)
        self.ai_bot = create_bot(bot_type)

        self.role = Role().roles['验证码识别']
        self.role_play = RolePlay(self.ai_bot, 'verification_code_session', self.role['descn'], self.role['wrapper'])

    # 异步初始化
    async def async_init(self):
        return

    @on_link_share_message(priority=99)
    async def handle_link_share(self, bot: WechatAPIClient, message: dict):
        if not message['FromWxid'] == 'gh_8ec531665608' or not message.get('url', ''):
            return PLUGIN_PASS
        # pushplus推送的短信
        url, pattern, html = message.get('url'), r"#!#(.*?)#!#", ''
        try:
            html = requests.get(url).text
        except Exception as e:
            logger.error("Smsforward 解析pushplus失败.", e)
            return PLUGIN_ENDED

        sms = re.search(pattern, html)
        sms = sms.group(1) if sms else ''

        self.role_play.reset()
        context = Context(ContextType.TEXT, self.role_play.action(sms))
        context.kwargs = dict()
        context["session_id"] = self.role_play.sessionid
        context["openai_api_key"] = self.api_key
        context["openai_api_base"] = self.api_base
        context["gpt_model"] = self.model
        reply = self.ai_bot.reply(sms, context)

        await bot.send_link_message(self.send_to, url, reply.content, sms.strip('#!#'), self.link_icon)
        # await bot.send_text_message(self.send_to, reply.content)

        return PLUGIN_ENDED




