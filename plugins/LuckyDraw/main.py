import random
import tomllib

from loguru import logger

from WechatAPI import WechatAPIClient
from database.XYBotDB import XYBotDB
from utils.decorators import *
from utils.plugin_base import PluginBase


class LuckyDraw(PluginBase):
    description = "幸运抽奖"
    author = "HenryXiaoYang"
    version = "1.0.0"

    def __init__(self):
        super().__init__()

        with open("plugins/LuckyDraw/config.toml", "rb") as f:
            plugin_config = tomllib.load(f)

        config = plugin_config["LuckyDraw"]

        self.enable = config["enable"]
        self.command = config["command"]
        self.command_format = config["command-format"]

        probabilities = config["probabilities"]
        self.probabilities = {}
        for item in probabilities.values():
            name = item["name"]
            cost = item["cost"]
            probability = item["probability"]
            self.probabilities[name] = {"cost": cost, "probability": probability}

        self.max_draw = config["max-draw"]
        self.draw_per_guarantee = config["draw-per-guarantee"]
        self.guaranteed_max_probability = config["guaranteed-max-probability"]

        self.db = XYBotDB()

    @on_text_message
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return

        content = str(message["Content"]).strip()
        command = content.split(" ")

        if not len(command) or command[0] not in self.command:
            return

        target_wxid = message["SenderWxid"]
        target_points = self.db.get_points(target_wxid)

        if len(command) < 2:
            await bot.send_at_message(message["FromWxid"], self.command_format, [target_wxid])
            return

        draw_name = command[1]
        if draw_name not in self.probabilities.keys():
            await bot.send_text_message(message["FromWxid"], "🤔你指定的奖池无效哦！")
            return

        draw_count = 1
        if len(command) == 3 and command[2].isdigit():
            draw_count = int(command[2])

        if draw_count > self.max_draw:
            await bot.send_text_message(message["FromWxid"], f"😔你最多只能抽{self.max_draw}次哦！")
            return

        if target_points < self.probabilities[draw_name]["cost"] * draw_count:
            await bot.send_text_message(message["FromWxid"],
                                        f"😭你积分不足以你抽{draw_count}次{draw_name}抽奖哦！")
            return

        draw_probability = self.probabilities[draw_name]["probability"]
        cost = self.probabilities[draw_name]["cost"] * draw_count

        self.db.add_points(target_wxid, -cost)

        wins = []

        # 保底抽奖
        min_guaranteed = draw_count // self.draw_per_guarantee  # 保底抽奖次数
        for _ in range(min_guaranteed):  # 先把保底抽了
            random_num = random.uniform(0, self.guaranteed_max_probability)
            cumulative_probability = 0
            for p, prize in draw_probability.items():
                cumulative_probability += float(p)
                if random_num <= cumulative_probability:
                    win_name = prize["name"]
                    win_points = prize["points"]
                    win_symbol = prize["symbol"]

                    wins.append(
                        (win_name, win_points, win_symbol)
                    )  # 把结果加入赢取列表
                    break

            # 正常抽奖
        for _ in range(draw_count - min_guaranteed):  # 把剩下的抽了
            random_num = random.uniform(0, 1)
            cumulative_probability = 0
            for p, prize in draw_probability.items():
                cumulative_probability += float(p)
                if random_num <= cumulative_probability:
                    win_name = prize["name"]
                    win_points = prize["points"]
                    win_symbol = prize["symbol"]

                    wins.append(
                        (win_name, win_points, win_symbol)
                    )  # 把结果加入赢取列表
                    break

        total_win_points = 0
        for win_name, win_points, win_symbol in wins:  # 统计赢取的积分
            total_win_points += win_points

        self.db.add_points(target_wxid, total_win_points)  # 把赢取的积分加入数据库
        logger.info(f"用户 {target_wxid} 在 {draw_name} 抽了 {draw_count}次 赢取了{total_win_points}积分")
        output = self.make_message(wins, draw_name, draw_count, total_win_points, cost)
        await bot.send_at_message(message["FromWxid"], output, [target_wxid])

    @staticmethod
    def make_message(
            wins, draw_name, draw_count, total_win_points, draw_cost
    ):  # 组建信息
        name_max_len = 0
        for win_name, win_points, win_symbol in wins:
            if len(win_name) > name_max_len:
                name_max_len = len(win_name)

        begin_message = f"\n----XYBot抽奖----\n🥳恭喜你在 {draw_count}次 {draw_name}抽奖 中抽到了：\n\n"
        lines = []
        for _ in range(name_max_len + 2):
            lines.append("")

        begin_line = 0

        one_line_length = 0

        for win_name, win_points, win_symbol in wins:
            if one_line_length >= 10:  # 每行10个结果，以免在微信上格式错误
                begin_line += name_max_len + 2
                for _ in range(name_max_len + 2):
                    lines.append("")  # 占个位
                one_line_length = 0

            lines[begin_line] += win_symbol
            for i in range(begin_line + 1, begin_line + name_max_len + 1):
                if i % (name_max_len + 2) <= len(win_name):
                    lines[i] += (
                            "\u2004" + win_name[i % (name_max_len + 2) - 1]
                    )  # \u2004 这个空格最好 试过了很多种空格
                else:
                    lines[i] += win_symbol
            lines[begin_line + name_max_len + 1] += win_symbol

            one_line_length += 1

        message = begin_message
        for line in lines:
            message += line + "\n"

        message += f"\n\n🎉总计赢取积分: {total_win_points}🎉\n🎉共计消耗积分：{draw_cost}🎉\n\n概率请自行查询菜单⚙️"

        return message
