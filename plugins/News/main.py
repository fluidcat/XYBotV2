import asyncio
import tomllib
from datetime import datetime
from random import sample

import aiohttp

from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.plugin_base import PluginBase
from loguru import logger
from utils import const
import html


class News(PluginBase):
    description = "新闻插件"
    author = "HenryXiaoYang"
    version = "1.1.0"

    # Change Log
    # 1.1.0 2025/2/22 默认关闭定时新闻

    def __init__(self):
        super().__init__()

        with open("plugins/News/config.toml", "rb") as f:
            plugin_config = tomllib.load(f)

        config = plugin_config["News"]

        self.enable = config["enable"]
        self.enable_schedule = config["enable-schedule"]
        self.command = config["command"]

    @on_text_message
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return
        command = message.get('command')
        if not command.startswith('#'):
            return
        if command.lower().removeprefix('#') not in self.command:
            return

        message['reply_ats'] = [message['SenderWxid']] if message['IsGroup'] else []
        finish = True
        news_txt = None
        # 头条、历史今日、GitHub榜单
        if "头条" in command:
            news_txt = await self.get_news('netease_news', 10)
        elif "历史" in command:
            news_txt = await self.get_news('history')
        elif "github" in command.lower():
            news_txt = await self.get_news('github', desc=True)
        else:
            finish = False

        if finish:
            await bot.send_reply_message(message, news_txt if news_txt else command + " 获取失败！")
        else:
            # 其他新闻
            async with aiohttp.ClientSession() as session:
                async with session.get("http://zj.v.api.aa1.cn/api/60s-v2/?cc=fluidcat") as resp:
                    image_byte = await resp.read()
            await bot.send_image_message(message["FromWxid"], image_byte)

    @on_at_message
    async def handle_at(self, bot: WechatAPIClient, message: dict):
        return await self.handle_text(bot, message)

    async def get_news(self, topic='netease_news', size=None, desc=False):
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            # history 历史今天 github github热榜 netease_news 网易新闻
            async with session.get("https://api.98dou.cn/api/hotlist?type=" + topic) as resp:
                data = await resp.json()

        if not data["success"]:
            logger.debug(f"get_news 失败: {data}")
            return None
        result = data.get("data", {})
        if topic == 'history':
            result = list(filter(lambda e: '出生' not in e.get('title'), result))
        if not len(result):
            return None
        if size:
            result = sample(result, size)
        if desc:
            titles = ['\n'.join([item["title"], item["desc"] + '\n']) for item in result if "title" in item]
        else:
            titles = [html.unescape(item["title"]) for item in result if "title" in item]
        news = "\n".join([f"{const.NUMBERS[i + 1]} {word}" for i, word in enumerate(titles)])
        return news

    @schedule('cron', hour='7,12,18,21', jitter=30 * 60)
    async def schedule_msg(self, bot: WechatAPIClient):
        news = f'📰新闻快报  {datetime.now().strftime("%H:%M")}📰\n\n' + await self.get_news('netease_news', 15)
        await self.send_mass(bot, news)

    @schedule('cron', hour='8', jitter=30 * 60)
    async def daily_news(self, bot: WechatAPIClient):
        today = datetime.now().strftime("%m月%d日")
        history = f'🕰历史今天  {today}🕰\n\n' + await self.get_news('history')
        github = f'🔝GitHub  {today}🔝\n' + await self.get_news('github', desc=True)

        await self.send_mass(bot, history)
        await self.send_mass(bot, github)

    # @schedule('cron', hour=12)
    async def noon_news(self, bot: WechatAPIClient):
        if not self.enable_schedule_news:
            return
        id_list = []
        wx_seq, chatroom_seq = 0, 0
        while True:
            contact_list = await bot.get_contract_list(wx_seq, chatroom_seq)
            id_list.extend(contact_list["ContactUsernameList"])
            wx_seq = contact_list["CurrentWxcontactSeq"]
            chatroom_seq = contact_list["CurrentChatRoomContactSeq"]
            if contact_list["CountinueFlag"] != 1:
                break

        chatrooms = []
        for id in id_list:
            if id.endswith("@chatroom"):
                chatrooms.append(id)

        async with aiohttp.ClientSession() as session:
            async with session.get("http://zj.v.api.aa1.cn/api/60s-v2/?cc=XYBot") as resp:
                iamge_byte = await resp.read()

        for id in chatrooms:
            await bot.send_image_message(id, iamge_byte)
            await asyncio.sleep(2)

    # @schedule('cron', hour=18)
    async def night_news(self, bot: WechatAPIClient):
        if not self.enable_schedule_news:
            return
        id_list = []
        wx_seq, chatroom_seq = 0, 0
        while True:
            contact_list = await bot.get_contract_list(wx_seq, chatroom_seq)
            id_list.extend(contact_list["ContactUsernameList"])
            wx_seq = contact_list["CurrentWxcontactSeq"]
            chatroom_seq = contact_list["CurrentChatRoomContactSeq"]
            if contact_list["CountinueFlag"] != 1:
                break

        chatrooms = []
        for id in id_list:
            if id.endswith("@chatroom"):
                chatrooms.append(id)

        async with aiohttp.ClientSession() as session:
            async with session.get("http://v.api.aa1.cn/api/60s-v3/?cc=XYBot") as resp:
                iamge_byte = await resp.read()

        for id in chatrooms:
            await bot.send_image_message(id, iamge_byte)
            await asyncio.sleep(2)
