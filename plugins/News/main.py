import asyncio
import tomllib
from random import sample

import aiohttp

from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.plugin_base import PluginBase
from loguru import logger


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
        self.enable_schedule_news = config["enable-schedule-news"]
        self.command = config["command"]

    @on_text_message
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return
        command = str(message["Content"]).strip().split(" ")
        if not command[0].startswith('#'):
            return
        if command[0].lower().removeprefix('#') not in self.command:
            return

        ats = [message['SenderWxid']] if message['IsGroup'] else []
        finish = True
        news_txt = None
        # 头条、历史今日、GitHub榜单
        if "头条" in command[0]:
            news_txt = await self.get_news('history', 10)
        elif "历史" in command[0]:
            news_txt = await self.get_news('history')
        elif "github" in command[0]:
            news_txt = await self.get_news('github', desc=True)
        else:
            finish = False

        if finish:
            if not news_txt:
                await bot.send_at_message(message["FromWxid"], command[0] + " 获取失败！", ats)
            else:
                news_txt = '\n' + news_txt if ats else news_txt
                await bot.send_at_message(message["FromWxid"], news_txt, ats)
        else:
            # 其他新闻
            async with aiohttp.ClientSession() as session:
                async with session.get("http://zj.v.api.aa1.cn/api/60s-v2/?cc=XYBot") as resp:
                    image_byte = await resp.read()
            await bot.send_image_message(message["FromWxid"], image_byte)

    async def get_news(self, topic='netease_news', size=None, desc=False):
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            # history 历史今天 github github热榜 netease_news 网易新闻
            async with session.get("https://api.98dou.cn/api/hotlist?type=" + topic) as resp:
                data = await resp.json()

        if not data["success"]:
            logger.debug(f"get_news 失败: {data}")
            return None
        result = data.get("data", {})
        if not len(result):
            return None
        if size:
            result = sample(result, size)
        if desc:
            titles = ['\n'.join([item["title"], item["desc"] + '\n']) for item in result if "title" in item]
        else:
            titles = [item["title"] for item in result if "title" in item]
        news = "\n".join([f"{i + 1}. {word}" for i, word in enumerate(titles)])
        return news

    @schedule('cron', hour=12)
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

    @schedule('cron', hour=18)
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
