import html
import re

import requests
from loguru import logger
import tomllib  # 确保导入tomllib以读取配置文件
import os  # 确保导入os模块

from WechatAPI import WechatAPIClient
from plugins.LLMBridge.LLMBridge_config import load_config, conf
from plugins.LLMBridge.bot.bot_factory import create_bot
from plugins.LLMBridge.bridge.bridge import Bridge
from plugins.LLMBridge.bridge.context import Context, ContextType
from plugins.LLMBridge.role import Role, RolePlay
from utils.const import PLUGIN_PASS, PLUGIN_ENDED
from utils.decorators import *
from utils.plugin_base import PluginBase
from urllib.parse import urlparse


class ArticleSummary(PluginBase):
    description = "文章总结插件"
    author = "fluidcat"
    version = "1.0.0"

    # 同步初始化
    def __init__(self):
        super().__init__()

        # 获取配置文件路径
        config_path = os.path.join(os.path.dirname(__file__), "config.toml")
        config = self.loadConfig(config_path).get('ArticleSummary', {})

        self.enable = config.get("enable", False)
        self.max_words = config.get("max_words", 8000)
        self.jina_reader_base = config.get("jina_reader_base")
        self.white_url_list = config.get("white_url_list")
        self.black_url_list = config.get("black_url_list")
        self.prompt = config.get("prompt")

        load_config()
        open_ai_config = conf().get("open_ai_compatible").get(config.get('open_ai_compatible', 'wwxq'))
        self.api_key = open_ai_config.get('open_ai_api_key')
        self.api_base = open_ai_config.get('open_ai_api_base')
        self.model = open_ai_config.get('model')

        bot_type = Bridge().infer_bot_type(self.model)
        self.ai_bot = create_bot(bot_type)

        self.role = Role().roles['链接文章总结']
        self.role_play = RolePlay(self.ai_bot, 'article_summary_session', self.role['descn'], self.role['wrapper'])

    @on_text_message(priority=79)
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        msg = message['Content']

        is_url, jina_result = self.jina_url_convert(msg)
        if not is_url or not jina_result:
            return PLUGIN_PASS

        return await self.handle_summary(jina_result, bot, message)

    @on_at_message(priority=79)
    async def handle_at(self, bot: WechatAPIClient, message: dict):
        msg = message['Content']

        is_url, jina_result = self.jina_url_convert(msg)
        if not is_url and not jina_result:
            return PLUGIN_PASS

        return await self.handle_summary(jina_result, bot, message)

    @on_file_message(priority=79)
    async def handle_file(self, bot: WechatAPIClient, message: dict):
        logger.info("收到了文件消息")

    @on_quote_message(priority=79)
    async def handle_quote(self, bot: WechatAPIClient, message: dict):
        logger.info("收到了引用消息")

    @on_link_share_message(priority=79)
    async def handle_link_share(self, bot: WechatAPIClient, message: dict):
        if not message.get('url', ''):
            return PLUGIN_PASS

        is_url, jina_result = self.jina_url_convert(message.get('url'))
        if not is_url and not jina_result:
            return PLUGIN_PASS

        return await self.handle_summary(jina_result, bot, message)

    async def handle_summary(self, article: str, bot: WechatAPIClient, message: dict):

        self.role_play.reset()
        context = Context(ContextType.TEXT, self.role_play.action(article))
        context.kwargs = dict()
        context["session_id"] = self.role_play.sessionid
        context["openai_api_key"] = self.api_key
        context["openai_api_base"] = self.api_base
        context["gpt_model"] = self.model
        reply = self.ai_bot.reply(article, context)
        await bot.send_reply_message(message, reply.content)

        return PLUGIN_ENDED

    def jina_url_convert(self, url: str, retry_count: int = 0):
        is_url, jina_result = True, ''
        try:
            is_url = self._check_url(url)
            if not is_url:
                return is_url, jina_result

            target_url = html.unescape(url)  # 解决公众号卡片链接校验问题
            jina_url = self.jina_reader_base + "/" + target_url
            logger.info(f"jina_url：{jina_url}")
            headers = {
                "X-Retain-Images": "none",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            }
            response = requests.get(jina_url, headers=headers, timeout=60)
            response.raise_for_status()
            # 删除链接
            target_url_content = self.remove_all_links(response.text)

            return is_url, target_url_content[:self.max_words]
        except Exception as e:
            if retry_count < 3:
                logger.warning(f"[jina_url_convert] {str(e)}, retry {retry_count + 1}")
                return self.jina_url_convert(url, retry_count + 1)
            return is_url, jina_result

    def remove_all_links(self, markdown_text):
        # 处理行内链接
        text = re.sub(r'\[([^\]]*)\]\([^)]*\)', '', markdown_text)
        # 处理引用链接
        text = re.sub(r'\[([^\]]*)\]\[[^\]]*\]', '', text)
        text = re.sub(r'^\[[^\]]*\]:\s*\S+\s*$', '', text, flags=re.MULTILINE)
        # 处理自动链接
        text = re.sub(r'<\S+>', '', text)
        # 删除空行（包括只包含空白字符的行）
        text = re.sub(r'\n[\s\*]*\n', '\n', text)
        return text.strip()

    def _check_url(self, target_url: str):
        stripped_url = target_url.strip()

        # 简单校验是否是url
        try:
            result = urlparse(stripped_url)
            is_url = all([result.scheme, result.netloc])  # 必须有协议和域名
        except:
            is_url = False
        if not is_url:
            return False

        # 检查白名单
        if len(self.white_url_list):
            if not any(stripped_url.startswith(white_url) for white_url in self.white_url_list):
                return False

        # 排除黑名单，黑名单优先级>白名单
        for black_url in self.black_url_list:
            if stripped_url.startswith(black_url):
                return False

        return True
