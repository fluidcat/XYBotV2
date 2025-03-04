import tomllib
from datetime import datetime
from random import randint

import pytz

from WechatAPI import WechatAPIClient
from database.XYBotDB import XYBotDB
from utils.decorators import *
from utils.plugin_base import PluginBase


class SignIn(PluginBase):
    description = "每日签到"
    author = "HenryXiaoYang"
    version = "1.0.0"

    def __init__(self):
        super().__init__()

        with open("plugins/SignIn/config.toml", "rb") as f:
            plugin_config = tomllib.load(f)

        with open("main_config.toml", "rb") as f:
            main_config = tomllib.load(f)

        config = plugin_config["SignIn"]
        main_config = main_config["XYBot"]

        self.enable = config["enable"]
        self.command = config["command"]
        self.min_points = config["min-point"]
        self.max_points = config["max-point"]
        self.streak_cycle = config["streak-cycle"]
        self.max_streak_point = config["max-streak-point"]

        self.timezone = main_config["timezone"]

        self.db = XYBotDB()

        # 每日签到排名数据
        self.today_signin_count = 0
        self.last_reset_date = datetime.now(tz=pytz.timezone(self.timezone)).date()

    def _check_and_reset_count(self):
        current_date = datetime.now(tz=pytz.timezone(self.timezone)).date()
        if current_date != self.last_reset_date:
            self.today_signin_count = 0
            self.last_reset_date = current_date

    @on_text_message
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return

        content = str(message["Content"]).strip()
        command = content.split(" ")

        if not len(command) or command[0] not in self.command:
            return

        # 检查是否需要重置计数
        self._check_and_reset_count()

        sign_wxid = message["SenderWxid"]

        last_sign = self.db.get_signin_stat(sign_wxid)
        now = datetime.now(tz=pytz.timezone(self.timezone)).replace(hour=0, minute=0, second=0, microsecond=0)

        # 确保 last_sign 用了时区
        if last_sign and last_sign.tzinfo is None:
            last_sign = pytz.timezone(self.timezone).localize(last_sign)
        last_sign = last_sign.replace(hour=0, minute=0, second=0, microsecond=0)

        if last_sign and (now - last_sign).days < 1:
            output = "\n你今天已经签到过了！😠"
            await bot.send_at_message(message["FromWxid"], output, [sign_wxid])
            return

        # 检查是否断开连续签到（超过1天没签到）
        if last_sign and (now - last_sign).days > 1:
            old_streak = self.db.get_signin_streak(sign_wxid)
            streak = 1  # 重置连续签到天数
            streak_broken = True
        else:
            old_streak = self.db.get_signin_streak(sign_wxid)
            streak = old_streak + 1 if old_streak else 1  # 如果是第一次签到，从1开始
            streak_broken = False

        self.db.set_signin_stat(sign_wxid, now)
        self.db.set_signin_streak(sign_wxid, streak)  # 设置连续签到天数
        streak_points = min(streak // self.streak_cycle, self.max_streak_point)  # 计算连续签到奖励

        signin_points = randint(self.min_points, self.max_points)  # 随机积分
        self.db.add_points(sign_wxid, signin_points + streak_points)  # 增加积分

        # 增加签到计数并获取排名
        self.today_signin_count += 1
        today_rank = self.today_signin_count

        output = ("\n"
                  f"签到成功！你领到了 {signin_points} 个积分！✅\n"
                  f"你是今天第 {today_rank} 个签到的！🎉\n")

        if streak_broken and old_streak > 0:  # 只有在真的断签且之前有签到记录时才显示
            output += f"你断开了 {old_streak} 天的连续签到！[心碎]"
        elif streak > 1:
            output += f"你连续签到了 {streak} 天！"

        if streak_points > 0:
            output += f" 再奖励 {streak_points} 积分！"

        if streak > 1 and not streak_broken:
            output += "[爱心]"

        await bot.send_at_message(message["FromWxid"], output, [sign_wxid])
