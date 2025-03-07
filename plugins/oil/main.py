import tomllib
from datetime import datetime

import aiohttp
import jieba
from loguru import logger

from WechatAPI import WechatAPIClient
from utils.daily_cache import daily_cache
from utils.decorators import *
from utils.plugin_base import PluginBase
from plugins.oil.table_image import draw


class OilPrice(PluginBase):
    description = "油价插件"
    author = "fluidcat"
    version = "1.0.0"

    def __init__(self):
        super().__init__()

        with open("plugins/oil/config.toml", "rb") as f:
            plugin_config = tomllib.load(f)

        config = plugin_config["OilPrice"]

        self.enable = config["enable"]
        self.command = config["command"]
        self.schedule_province = config["schedule-province"]
        self.enable_schedule = config["enable-schedule"]

    @on_text_message
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        command = message.get('command')
        if not command.startswith('#'):
            return
        # 今日油价，油价，广东油价，92油价，92号油价，广东92油价
        cmds = jieba.cut(command)
        if '油价' not in cmds:
            return

        data = await self.get_oil_data()
        image = draw(data)
        await bot.send_image_message(message["FromWxid"], image)

    @on_at_message
    async def handle_at(self, bot: WechatAPIClient, message: dict):
        return await self.handle_text(bot, message)

    @schedule('cron', hour='9', jitter=30 * 60)
    async def daily_notify(self, bot: WechatAPIClient):
        list_json = await self.get_oil_data()
        oil = [[item.get(p) for p in self.schedule_province] for item in list_json]
        _92, _95, _98, _cy = oil
        width = 7
        blank = '\u2002'
        now = datetime.now()
        msg = (
            f"🛢️油价快报  {now.month}月{now.day}日🛢️\n"
            f"　　　{'92# ':{blank}<{width}}{'95# ':{blank}<{width}}{'98# ':{blank}<{width}}柴油\n"
        )
        for i, p in enumerate(self.schedule_province):
            msg += f"{p}　{_92[i]:{blank}<{width}}{_95[i]:{blank}<{width}}{_98[i]:{blank}<{width}}{_cy[i]}\n"

        await self.send_mass(bot, msg.strip())

    @daily_cache
    async def get_oil_data(self):
        all_types = ['92', '95', '98', 'chaiyou']
        data = []
        session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        for oil_type in all_types:
            async with session.get("https://api.guiguiya.com/api/youjia?region=" + oil_type) as resp:
                json = await resp.json()
            logger.info(f"获取{oil_type}油价：{json}")
            if json.get('code', 0) == 200 and json.get('data', None):
                data.append(json.get('data'))
            else:
                data.append({})
        await session.close()
        return data
