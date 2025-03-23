import imghdr
import io

import aiohttp
from loguru import logger

from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.plugin_base import PluginBase


class UpdateQR(PluginBase):
    description = "更新群二维码"
    author = "HenryXiaoYang"
    version = "1.0.0"

    def __init__(self):
        super().__init__()

    @on_text_message
    async def on_text(self, bot: WechatAPIClient, message: dict):
        if message.get("Content") == "更新群二维码":
            await self.update_qr(bot)

    @schedule('cron', day_of_week='mon', hour=8)
    async def monday_update_qr(self, bot: WechatAPIClient):
        await self.update_qr(bot)

    @schedule('cron', day_of_week='thu', hour=8)
    async def thursday_update_qr(self, bot: WechatAPIClient):
        await self.update_qr(bot)

    @staticmethod
    async def update_qr(bot: WechatAPIClient):
        qr = await bot.get_chatroom_qrcode("56994401945@chatroom")
        qr = bot.base64_to_byte(qr.get("base64", ""))

        img_format = imghdr.what(io.BytesIO(qr))

        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer Henry_Yang"}
            data = aiohttp.FormData()
            data.add_field('file',
                           qr,
                           filename=f'qr_code.{img_format}',
                           content_type=f'image/{img_format}')

            async with session.post("https://qrcode.yangres.com/update_image", headers=headers, data=data) as response:
                if response.status != 200:
                    logger.error("上传失败: HTTP {}", response.status)
                    logger.error(await response.text())
                else:
                    logger.success("更新群二维码成功")
