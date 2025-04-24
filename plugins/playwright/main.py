from typing import Optional

import filetype
import jieba
from loguru import logger

from WechatAPI import WechatAPIClient
from plugins.playwright.PlaywrightChat import BrowserManager, BrowserPage
from utils.const import PLUGIN_ENDED
from utils.decorators import *
from utils.plugin_base import PluginBase


class Playwright(PluginBase):
    description = "Playwright AI"
    author = "fluidcat"
    version = "1.1.0"

    # todo
    # 1、删除记忆
    # 2、上传图片
    # 3、上传文件
    # 4、上传图片
    # 5、生成语音

    def __init__(self):
        super().__init__()

        plugin_config = self.loadConfig("plugins/playwright/config.toml")
        config = plugin_config["Playwright"]
        self.enable = config["enable"]

        self.cdp_url = "ws://192.168.2.2:3000"
        # self.cdp_url = "http://127.0.0.1:9222"
        # self.cdp_url = "ws://127.0.0.1:3000"
        self.browser = BrowserManager(cdp_url=self.cdp_url)

    async def async_init(self):
        await self.browser.__aenter__()

    async def on_disable(self):
        await self.browser.__aexit__()

    async def check_login(self, conversation_id: str, bot: WechatAPIClient, message: dict):
        browser_page = await self.browser.get_or_create_page(conversation_id)
        # 已经登录
        if await browser_page.is_login():
            return True

        # 登录流程
        result = await self.ai_login(conversation_id, message.get('command'))
        if result:
            await bot.send_reply_message(message, result)
            return False

        await bot.send_reply_message(message, "AI服务尚未登录")
        return False

    async def ai_login(self, conversation_id: str, command: str):
        browser_page = await self.browser.get_or_create_page(conversation_id)
        if command.startswith('登录'):
            cmds = command.split(" ")
            phone = cmds[1] if len(cmds) == 2 else '19520652064'
            await browser_page.login(phone)
            return '已发送验证码'

        elif command.startswith('验证码'):
            cmds = jieba.cut(command)
            code = cmds[1] if len(cmds) == 2 else ''
            if code:
                await browser_page.verify_login(code)
                return "登录成功"
            else:
                return "验证码为空，登录失败"

    async def handle_command(self, bot: WechatAPIClient, message: dict):
        page: Optional[BrowserPage] = None
        try:
            cmd = message.get('command')
            if cmd == '删除记忆':
                conversation_id = message['FromWxid']
                page = await self.browser.get_or_create_page(conversation_id)
                if page:
                    await page.delete_memory()
                    await self.browser.close(conversation_id)
                await bot.send_reply_message(message, "记忆已删除")
                return True
        except Exception as e:
            logger.exception("handle_command error.", e)
            if page:
                await page.page.screenshot(path="handle_command_error.png")

    @on_text_message(priority=29)
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        message['reply_ats'] = [message['SenderWxid']] if message['IsGroup'] else []

        if await self.handle_command(bot, message):
            return PLUGIN_ENDED

        query = message['Content']
        conversation_id = message['FromWxid']

        try:
            browser_page = await self.browser.get_or_create_page(conversation_id)
            if not await self.check_login(conversation_id, bot, message):
                return
            else:
                await browser_page.ready()

            await browser_page.sendMessage(query)
            answer = await browser_page.getMessage()

            await bot.send_reply_message(message, answer)
        except Exception as e:
            logger.exception('handle error', e)
            await self.browser.close(conversation_id)

    @on_at_message(priority=19)
    async def handle_at(self, bot: WechatAPIClient, message: dict):
        return await self.handle_text(bot, message)

    # @on_file_message(priority=20)
    async def handle_file(self, bot: WechatAPIClient, message: dict):
        conversation_id = message['FromWxid']
        try:
            browser_page = await self.browser.get_or_create_page(conversation_id)
            if not await self.check_login(conversation_id, bot, message):
                return
            else:
                await browser_page.ready()

            file_byte = bot.base64_to_byte(message["File"])
            await browser_page.upload_file(message['Filename'], file_byte)

            await browser_page.sendMessage("总结一下这个文件的内容")
            answer = await browser_page.getMessage()

            await bot.send_reply_message(message, answer)
        except Exception as e:
            logger.exception('handle error', e)
            await self.browser.close(conversation_id)
