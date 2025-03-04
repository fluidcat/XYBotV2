import base64
import random
import re
import time
import tomllib
from io import BytesIO

from PIL import Image, ImageDraw, ImageFilter
from captcha.image import ImageCaptcha
from loguru import logger

from WechatAPI import WechatAPIClient
from database.XYBotDB import XYBotDB
from utils.decorators import *
from utils.plugin_base import PluginBase


class RedPacket(PluginBase):
    description = "红包系统"
    author = "HenryXiaoYang"
    version = "1.0.0"

    def __init__(self):
        super().__init__()

        with open("plugins/RedPacket/config.toml", "rb") as f:
            plugin_config = tomllib.load(f)

        config = plugin_config["RedPacket"]

        self.enable = config["enable"]
        self.command_format = config["command-format"]
        self.max_point = config["max-point"]
        self.min_point = config["min-point"]
        self.max_packet = config["max-packet"]
        self.max_time = config["max-time"]

        self.red_packets = {}
        self.db = XYBotDB()

    @on_text_message
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return

        content = str(message["Content"]).strip()
        command = re.split(r'[\s\u2005]+', content)

        if not len(command):
            return

        if len(command) == 3 and command[0] == "发红包":
            await self.send_red_packet(bot, message, command)
        elif len(command) == 2 and command[0] == "抢红包":
            await self.grab_red_packet(bot, message, command)
        elif command[0] in ["发红包", "抢红包"]:
            await bot.send_text_message(message["FromWxid"], f"{self.command_format}")

    async def send_red_packet(self, bot: WechatAPIClient, message: dict, command: list):
        sender_wxid = message["SenderWxid"]
        from_wxid = message["FromWxid"]

        error = ""
        if not message["IsGroup"]:
            error = "\n红包只能在群里发！😔"
        elif not command[1].isdigit() or not command[2].isdigit():
            error = f"\n指令格式错误！\n{self.command_format}"
        elif int(command[1]) > self.max_point or int(command[1]) < self.min_point:
            error = f"\n⚠️积分无效！最大{self.max_point}，最小{self.min_point}！"
        elif int(command[2]) > self.max_packet:
            error = f"\n⚠️红包数量无效！最大{self.max_packet}个红包！"
        elif int(command[2]) > int(command[1]):
            error = "\n🔢红包数量不能大于红包积分！"
        elif self.db.get_points(sender_wxid) < int(command[1]):
            error = "\n😭你的积分不够！"

        if error:
            await bot.send_at_message(from_wxid, error, [sender_wxid])
            return

        points = int(command[1])
        amount = int(command[2])
        sender_nick = await bot.get_nickname(sender_wxid)

        points_list = self._split_integer(points, amount)

        # 生成验证码图片
        captcha, captcha_image = self._generate_captcha()

        # 加载红包背景图
        background = Image.open("resource/images/redpacket.png")

        # 调整验证码图片大小
        captcha_width = 400  # 进一步增加验证码宽度
        captcha_height = 150  # 进一步增加验证码高度
        captcha_image = captcha_image.resize((captcha_width, captcha_height))

        # 创建一个带有圆角矩形和模糊边缘效果的遮罩
        padding = 40  # 增加边缘空间
        mask = Image.new('L', (captcha_width + padding * 2, captcha_height + padding * 2), 0)
        draw = ImageDraw.Draw(mask)

        # 绘制圆角矩形
        radius = 20  # 圆角半径
        draw.rounded_rectangle(
            [padding, padding, captcha_width + padding, captcha_height + padding],
            radius=radius,
            fill=255
        )

        # 应用高斯模糊创建柔和边缘
        mask = mask.filter(ImageFilter.GaussianBlur(radius=20))

        # 创建一个新的白色背景图层用于验证码
        captcha_layer = Image.new('RGBA', (captcha_width + padding * 2, captcha_height + padding * 2),
                                  (255, 255, 255, 0))
        # 将验证码图片粘贴到图层的中心
        captcha_layer.paste(captcha_image, (padding, padding))
        # 应用模糊遮罩
        captcha_layer.putalpha(mask)

        # 计算验证码位置使其在橙色区域居中
        x = (background.width - (captcha_width + padding * 2)) // 2
        y = background.height - 320  # 调整位置

        # 将带有模糊边缘的验证码图片粘贴到背景图
        background.paste(captcha_layer, (x, y), captcha_layer)

        # 转换为base64
        buffer = BytesIO()
        background.save(buffer, format='PNG')
        image_base64 = base64.b64encode(buffer.getvalue()).decode()

        # 保存红包信息
        self.red_packets[captcha] = {
            "points": points,
            "amount": amount,
            "sender": sender_wxid,
            "list": points_list,
            "grabbed": [],
            "time": time.time(),
            "chatroom": from_wxid,
            "sender_nick": sender_nick
        }

        self.db.add_points(sender_wxid, -points)
        logger.info(f"用户 {sender_wxid} 发了个红包 {captcha}，总计 {points} 点积分")

        # 发送文字消息和图片
        text_content = (
            f"✨{sender_nick} 发送了一个红包！🧧\n"
            f"🥳快输入指令来抢红包！🎉\n"
            f"🧧指令：抢红包 口令"
        )

        await bot.send_text_message(from_wxid, text_content)
        await bot.send_image_message(from_wxid, image_base64)

    async def grab_red_packet(self, bot: WechatAPIClient, message: dict, command: list):
        grabber_wxid = message["SenderWxid"]
        from_wxid = message["FromWxid"]
        captcha = command[1]

        error = ""
        if captcha not in self.red_packets:
            error = "\n❌红包口令错误！"
        elif not self.red_packets[captcha]["list"]:
            error = "\n😭红包已被抢完！"
        elif not message["IsGroup"]:
            error = "\n红包只能在群里抢！😔"
        elif grabber_wxid in self.red_packets[captcha]["grabbed"]:
            error = "\n你已经抢过这个红包了！😡"
        elif self.red_packets[captcha]["sender"] == grabber_wxid:
            error = "\n😠不能抢自己的红包！"

        if error:
            await bot.send_at_message(from_wxid, error, [grabber_wxid])
            return

        try:
            grabbed_points = self.red_packets[captcha]["list"].pop()
            self.red_packets[captcha]["grabbed"].append(grabber_wxid)

            grabber_nick = await bot.get_nickname(grabber_wxid)
            self.db.add_points(grabber_wxid, grabbed_points)

            out_message = f"🧧恭喜 {grabber_nick} 抢到了 {grabbed_points} 点积分！👏"
            await bot.send_text_message(from_wxid, out_message)

            if not self.red_packets[captcha]["list"]:
                self.red_packets.pop(captcha)

        except IndexError:
            await bot.send_at_message(from_wxid, "\n红包已被抢完！😭", [grabber_wxid])

    @schedule('interval', seconds=300)
    async def check_expired_packets(self, bot: WechatAPIClient):
        logger.info("[计划任务]检查是否有超时的红包")
        for captcha in list(self.red_packets.keys()):
            packet = self.red_packets[captcha]
            if time.time() - packet["time"] > self.max_time:
                points_left = sum(packet["list"])
                sender_wxid = packet["sender"]
                chatroom = packet["chatroom"]
                sender_nick = packet["sender_nick"]

                self.db.add_points(sender_wxid, points_left)
                self.red_packets.pop(captcha)

                out_message = (
                    f"🧧发现有红包 {captcha} 超时！已归还剩余 {points_left} 积分给 {sender_nick}"
                )
                await bot.send_text_message(chatroom, out_message)

    @staticmethod
    def _generate_captcha():
        chars = "abdfghkmnpqtwxy23467889"
        captcha = ''.join(random.sample(chars, 5))

        image = ImageCaptcha().generate_image(captcha)
        return captcha, image

    @staticmethod
    def _split_integer(num: int, count: int) -> list:
        result = [1] * count
        remaining = num - count

        while remaining > 0:
            index = random.randint(0, count - 1)
            result[index] += 1
            remaining -= 1

        return result
