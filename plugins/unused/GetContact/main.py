import asyncio
import tomllib
from datetime import datetime

import aiohttp
from loguru import logger
from tabulate import tabulate

from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.plugin_base import PluginBase


class GetContact(PluginBase):
    description = "获取通讯录"
    author = "HenryXiaoYang"
    version = "1.0.0"

    def __init__(self):
        super().__init__()

        with open("plugins/GetContact/config.toml", "rb") as f:
            plugin_config = tomllib.load(f)

        with open("main_config.toml", "rb") as f:
            main_config = tomllib.load(f)

        config = plugin_config["GetContact"]
        main_config = main_config["XYBot"]

        self.enable = config["enable"]
        self.command = config["command"]

        self.admins = main_config["admins"]

    @on_text_message
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return

        content = str(message["Content"]).strip()
        command = content.split(" ")

        if not len(command) or command[0] not in self.command:
            return

        sender_wxid = message["SenderWxid"]

        if sender_wxid not in self.admins:
            await bot.send_text_message(message["FromWxid"], "❌你配用这个指令吗？😡")
            return

        a, b, c = await bot.send_text_message(message["FromWxid"], "正在获取通讯录信息，请稍等...")

        start_time = datetime.now()
        logger.info("开始获取通讯录信息时间：{}", start_time)

        id_list = []
        wx_seq, chatroom_seq = 0, 0
        while True:
            contact_list = await bot.get_contract_list(wx_seq, chatroom_seq)
            id_list.extend(contact_list["ContactUsernameList"])
            wx_seq = contact_list["CurrentWxcontactSeq"]
            chatroom_seq = contact_list["CurrentChatRoomContactSeq"]
            if contact_list["CountinueFlag"] != 1:
                break

        get_list_time = datetime.now()
        logger.info("获取通讯录信息列表耗时：{}", get_list_time - start_time)

        # 使用协程池处理联系人信息获取
        info_list = []

        async def fetch_contacts(id_chunk):
            contact_info = await bot.get_contact(id_chunk)
            return contact_info

        chunks = [id_list[i:i + 20] for i in range(0, len(id_list), 20)]

        sem = asyncio.Semaphore(20)

        async def worker(chunk):
            async with sem:
                return await fetch_contacts(chunk[:-1])  # 去掉最后一个ID，保持与原代码一致

        tasks = [worker(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks)

        # 合并结果
        for result in results:
            info_list.extend(result)

        done_time = datetime.now()
        logger.info("获取通讯录详细信息耗时：{}", done_time - get_list_time)
        logger.info("获取通讯录信息总耗时：{}", done_time - start_time)

        clean_info = []
        for info in info_list:
            if info.get("UserName", {}).get("string", ""):
                clean_info.append({
                    "Wxid": info.get("UserName", {}).get("string", ""),
                    "Nickname": info.get("NickName", {}).get("string", ""),
                    "Remark": info.get("Remark", {}).get("string"),
                    "Alias": info.get("Alias", "")})

        table = str(tabulate(clean_info, headers="keys", stralign="left"))

        payload = {"content": table}

        conn_ssl = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.request("POST", url="https://easychuan.cn/texts", connector=conn_ssl, json=payload) as req:
            resp = await req.json()
        await conn_ssl.close()

        await bot.send_link_message(message["FromWxid"],
                                    url=f"https://easychuan.cn/r/{resp['fetch_code']}?t=t",
                                    title="XYBot登录账号通讯录",
                                    description=f"过期时间：{resp['date_expire']}、耗时：{done_time - start_time}、点击查看详细通讯录信息", )

        await bot.revoke_message(message["FromWxid"], a, b, c)
