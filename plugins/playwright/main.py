import asyncio
from typing import Dict

import jieba
from loguru import logger

from WechatAPI import WechatAPIClient
from plugins.playwright.PlaywrightChat import BrowserManager
from utils.const import *
from utils.decorators import *
from utils.plugin_base import PluginBase


class Playwright(PluginBase):
    description = "Playwright AI"
    author = "fluidcat"
    version = "1.1.0"

    # todo 生成语音

    def __init__(self):
        super().__init__()

        plugin_config = self.loadConfig("plugins/playwright/config.toml")
        config = plugin_config["Playwright"]
        self.enable = config["enable"]

        self.cdp_url = config["cdp_url"]
        # self.cdp_url = "ws://127.0.0.1:3000"
        self.browser = BrowserManager(cdp_url=self.cdp_url)
        # 全局会话信号量字典，每个 conversation_id 对应独立的 Semaphore(1)
        self._semaphores: Dict[str, asyncio.Semaphore] = {}

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
        cmd: str = message.get('command').removeprefix('#')
        commands = ['删除记忆', ['使用聊天模型', '使用思考模型'], ['不联网', '联网搜索']]
        if not [c for c in commands if cmd == c or (isinstance(c, list) and cmd in c)]:
            return

        conversation_id = message['FromWxid']
        try:
            page = await self.get_page(bot, message)
            if not page:
                return PLUGIN_FALLBACK

            if cmd == commands[0]:
                await page.delete_memory()
                await self.browser.close(conversation_id)
                await bot.send_reply_message(message, "记忆已删除")

            elif cmd in commands[1]:
                model = 'deepseekV3' if cmd == '使用聊天模型' else 'deepseekR1'
                await page.changeModel(model)
                await bot.send_reply_message(message, f"已{cmd}")

            elif cmd in commands[2]:
                search = 'super_search' if cmd == '联网搜索' else 'no_search'
                await page.changeSearch(search)
                await bot.send_reply_message(message, f"已{cmd}")

        except Exception as e:
            logger.exception("handle_command error.", e)
        return PLUGIN_EXEC_FINISHED

    async def get_page(self, bot: WechatAPIClient, message: dict):
        try_count = 0
        while True:
            if try_count >= 5:
                return
            try:
                conversation_id = message['FromWxid']
                browser_page = await self.browser.get_or_create_page(conversation_id)
                if not await self.check_login(conversation_id, bot, message):
                    # 未登录
                    return
                else:
                    await browser_page.ready()
                return browser_page
            except Exception as e:
                try_count += 1
                logger.exception(f"get_page error, retry: {try_count}", e)

    @on_text_message(priority=40)
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        message['reply_ats'] = [message['SenderWxid']] if message['IsGroup'] else []

        if await self.handle_command(bot, message):
            return PLUGIN_ENDED
        if message.get('command', '').startswith('#'):
            return PLUGIN_PASS

        query = f"你是友好的助手，是叫[圆脸]的人的替身。1、根据对话历史和当前问题判断，涉及和老婆感情问题时需要表现出你很爱你的老婆；2、如果用户问题不涉及感情问题时你是一个没有感情的分析处理助手；3、回复问题时不要出现前面的设定逻辑\n用户对你说：{message['Content']}"
        # query = message['Content']
        conversation_id = message['FromWxid']
        # 获取或创建会话专属的信号量（保证同一会话串行）
        sem = self._semaphores.setdefault(conversation_id, asyncio.Semaphore(1))
        async with sem:
            try:
                if not (browser_page := await self.get_page(bot, message)):
                    return PLUGIN_FALLBACK

                await browser_page.sendMessage(query)
                answer = await browser_page.getMessage()

                await bot.send_reply_message(message, answer)
            except Exception as e:
                logger.exception('handle error', e)
                await self.browser.close(conversation_id)

        return PLUGIN_ENDED

    @on_at_message(priority=40)
    async def handle_at(self, bot: WechatAPIClient, message: dict):
        return await self.handle_text(bot, message)

    @on_file_message(priority=40)
    async def handle_file(self, bot: WechatAPIClient, message: dict):
        conversation_id = message['FromWxid']
        try:
            if not (browser_page := await self.get_page(bot, message)):
                return PLUGIN_FALLBACK

            file_byte = bot.base64_to_byte(message["File"])
            await browser_page.upload_file(message['Filename'], file_byte)

            await browser_page.changeSearch('no_search')
            await browser_page.sendMessage("总结一下这个文件的内容")
            answer = await browser_page.getMessage()

            await bot.send_reply_message(message, answer)

            await browser_page.changeSearch('super_search')
            await browser_page.remove_thumb()

        except Exception as e:
            logger.exception('handle error', e)
            await self.browser.close(conversation_id)
        return PLUGIN_ENDED

    @on_image_message(priority=40)
    async def handle_image(self, bot: WechatAPIClient, message: dict):
        conversation_id = message['FromWxid']
        try:
            if not (browser_page := await self.get_page(bot, message)):
                return PLUGIN_FALLBACK

            image = bot.base64_to_byte(message["Content"])
            await browser_page.upload_image(image)
            # await browser_page.changeSearch('no_search')
            await browser_page.sendMessage("分析一下图片")
            answer = await browser_page.getMessage()

            await bot.send_reply_message(message, answer)

            # await browser_page.changeSearch('super_search')
            await browser_page.remove_thumb()

        except Exception as e:
            logger.exception('handle error', e)
            await self.browser.close(conversation_id)
        return PLUGIN_ENDED

    def generate_voice_query(self, query):
        return query + """\n按照要求回复：
            1、文本整理 
            - 回复的文本句子，严格遵守字数90~100字要求（important！！！！！！） 
            - 回复中超过100字的句子，在不改变原来语意语境情况下，分割成两个或多个句子 
            - 回复中不超过90字的句子，在遵守“rule 2”的前提下 和后续连个或多个句子合并在一起 
            - 回复中一个句子单独一行，直接输出整理好的文字，不用添加其他的说明  
            
            2、注意文本规范化与清晰性 
            - 避免歧义：多音字、缩写、数字等需明确标注。例如，“2024年”应写为“二零二四年”避免读成“两千零二十四”  
            - 特殊符号处理：如“&”应写为“和”，“℃”改为“摄氏度”，确保合成语音准确  
            - 标点使用：合理使用逗号、句号控制停顿节奏，避免长句导致合成语音喘不过气  
            
            3、语言结构与流畅性 
            - 短句优先：拆解复杂句式。例如，“尽管天气不好，我们仍决定出发”改为“天气不好。但我们决定出发。”  
            - 序号词使用：如果内容是列表的形式，使用“第一、第二、第三"、“首先、然后、再者、接着、最后”类似的词，让语音更清晰 
            - 避免生僻词：技术术语或专有名词需提供拼音或替代读法（如“GPT”输出“G-P-T”）  
            - 多语言混合：中英文混用时标注语言标签，防止发音错误
            """
