import asyncio
import io
import os
import tomllib
from io import BytesIO

import aiohttp
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure

from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.plugin_base import PluginBase


class Warthunder(PluginBase):
    description = "战争雷霆玩家查询"
    author = "HenryXiaoYang"
    version = "1.1.0"

    # Change Log
    # 1.0.0 第一个版本
    # 1.1.0 适配新的api格式

    def __init__(self):
        super().__init__()

        with open("plugins/Warthunder/config.toml", "rb") as f:
            plugin_config = tomllib.load(f)

        config = plugin_config["Warthunder"]

        self.enable = config["enable"]
        self.command = config["command"]
        self.command_format = config["command-format"]

        self.font_path = "resource/font/华文细黑.ttf"

    @on_text_message
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return

        content = str(message["Content"]).strip()
        command = content.split(" ")

        if command[0] not in self.command:
            return

        if len(command) != 2:
            await bot.send_text_message(message["FromWxid"], self.command_format)
            return

        player_name = content[len(command[0]) + 1:]

        output = (f"\n"
                  f"正在查询玩家 {player_name} 的数据，请稍等...😄")
        a, b, c = await bot.send_at_message(message["FromWxid"], output, [message["SenderWxid"]])

        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://wtapi.yangres.com/player?nick={player_name}") as resp:
                data = await resp.json()

        if data["code"] == 404:
            await bot.send_at_message(message["FromWxid"],
                                      f"🈚️玩家不存在！\n请检查玩家昵称，区分大小写哦！",
                                      [message["SenderWxid"]])
            await bot.revoke_message(message["FromWxid"], a, b, c)
            return
        elif data["code"] == 500:
            await bot.send_at_message(message["FromWxid"],
                                      f"🙅对不起，API服务出现错误！\n请稍后再试！",
                                      [message["SenderWxid"]])
            await bot.revoke_message(message["FromWxid"], a, b, c)
            return
        elif data["code"] == 400:
            await bot.send_at_message(message["FromWxid"],
                                      f"🙅对不起，API客户端出现错误！\n请稍后再试！",
                                      [message["SenderWxid"]])
            await bot.revoke_message(message["FromWxid"], a, b, c)
            return

        image = await self.generate_card(data["data"])

        await bot.send_image_message(message["FromWxid"], image)
        await bot.revoke_message(message["FromWxid"], a, b, c)

    async def generate_card(self, data: dict):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._generate_card, data)

    def _generate_card(self, data: dict) -> bytes:
        width, height = 1800, 2560
        top_color = np.array([127, 127, 213])
        bottom_color = np.array([145, 234, 228])

        # 生成坐标网格
        y, x = np.indices((height, width))
        # 计算对角线权重（从左上到右下）
        weight = (x + y) / (width + height)

        # 向量化计算渐变
        gradient = top_color * (1 - weight[..., np.newaxis]) + bottom_color * weight[..., np.newaxis]
        gradient = gradient.astype(np.uint8)
        img = Image.fromarray(gradient).convert('RGBA')

        # 设置矩形参数
        margin = 50  # 边距
        radius = 30  # 圆角半径

        # 绘制半透明圆角矩形
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw_overlay = ImageDraw.Draw(overlay)
        draw_overlay.rounded_rectangle(
            (margin, margin, width - margin, height - margin),
            radius=radius,
            fill=(255, 255, 255, 180))
        img = Image.alpha_composite(img, overlay)

        # 开始画数据
        fm.fontManager.addfont(self.font_path)
        plt.rcParams['font.family'] = ['STXihei']
        plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
        plt.rcParams['font.size'] = 23
        # 使用自定义字体文件
        title_font = ImageFont.truetype(self.font_path, size=60)
        normal_font = ImageFont.truetype(self.font_path, size=45)

        draw = ImageDraw.Draw(img)

        # 最上方标题
        draw.text((80, 60), "XYBotV2 战争雷霆玩家查询", fill="black", font=title_font)

        # 头像
        avatar = self._download_avatar(data["avatar"]).resize((300, 300))
        img.paste(avatar, (80, 160))

        # 玩家基础信息
        clan_and_nick = f"{data['clan_name']}  {data['nickname']}" if data.get('clan_name') else data['nickname']
        draw.text((400, 160), clan_and_nick, fill="black", font=normal_font)
        draw.text((400, 250), f"等级: {data['player_level']}", fill="black", font=normal_font)
        draw.text((400, 340), f"注册日期: {data['register_date']}", fill="black", font=normal_font)

        # 载具数据饼图
        owned_vehicles = []
        country_labels = []
        country_translation = {'USA': '美国', 'USSR': '苏联', 'Germany': '德国', 'GreatBritain': '英国',
                               'Japan': '日本',
                               'China': '中国', 'Italy': '意大利', 'France': '法国', 'Sweden': '瑞典',
                               'Israel': '以色列'}

        countries = dict(data["vehicles_and_rewards"]).keys()
        for c in countries:
            vehicles = data["vehicles_and_rewards"][c].get("owned_vehicles", 0)
            if vehicles > 0:
                owned_vehicles.append(vehicles)
                country_labels.append(country_translation.get(c, c))

        if owned_vehicles:
            fig = Figure(figsize=(6, 6), facecolor=(0, 0, 0, 0))
            ax = fig.add_subplot(111)

            color = plt.cm.Pastel1(np.linspace(0, 1, len(owned_vehicles)))  # 使用柔和的颜色方案
            ax.pie(owned_vehicles,
                   labels=country_labels,
                   autopct=lambda pct: self._show_actual(pct, owned_vehicles),
                   pctdistance=0.5,
                   labeldistance=1.1,
                   colors=color)
            ax.set_title('载具数据', fontsize=27)

            canvas = FigureCanvas(fig)
            buf = BytesIO()
            canvas.print_png(buf)
            buf.seek(0)
            pie_img = Image.open(buf)

            pie_img = pie_img.resize((650, 650))
            img.alpha_composite(pie_img, (1000, 40))

        # KDA数据
        total_kills = 0
        total_deaths = 0
        for mode in ['arcade', 'realistic', 'simulation']:
            stats = data.get('statistics', {}).get(mode, {})
            total_kills += stats.get('air_targets_destroyed', 0)
            total_kills += stats.get('ground_targets_destroyed', 0)
            total_kills += stats.get('naval_targets_destroyed', 0)
            total_deaths += stats.get('deaths', 0)
        kda = round(total_kills / total_deaths if total_deaths > 0 else 0, 2)

        draw.text((80, 480), f"KDA数据:", fill="black", font=title_font)
        draw.text((75, 560), f"击杀: {total_kills}", fill="black", font=normal_font)
        draw.text((350, 560), f"死亡: {total_deaths}", fill="black", font=normal_font)
        draw.text((600, 560), f"KDA: {kda}", fill="black", font=normal_font)

        title_font = title_font.font_variant(size=45)
        normal_font = normal_font.font_variant(size=35)

        # 数据部分
        titles = {"victories": "获胜数", "completed_missions": "完成任务", "victories_battles_ratio": "胜率",
                  "deaths": "死亡数", "lions_earned": "获得银狮", "play_time": "游玩时间",
                  "air_targets_destroyed": "击毁空中目标", "ground_targets_destroyed": "击毁地面目标",
                  "naval_targets_destroyed": "击毁海上目标"}
        air_titles = {"air_battles": "空战次数", "total_targets_destroyed": "共击毁目标",
                      "air_targets_destroyed": "击毁空中目标", "ground_targets_destroyed": "击毁地面目标",
                      "naval_targets_destroyed": "击毁海上目标", "air_battles_fighters": "战斗机次数",
                      "air_battles_bombers": "轰炸机次数", "air_battles_attackers": "攻击机次数",
                      "time_played_air_battles": "空战时长", "time_played_fighter": "战斗机时长",
                      "time_played_bomber": "轰炸机时长", "time_played_attackers": "攻击机时长"}
        ground_titles = {"ground_battles": "陆战次数", "total_targets_destroyed": "共击毁目标",
                         "air_targets_destroyed": "击毁空中目标", "ground_targets_destroyed": "击毁地面目标",
                         "naval_targets_destroyed": "击毁海上目标", "ground_battles_tanks": "坦克次数",
                         "ground_battles_spgs": "坦歼次数", "ground_battles_heavy_tanks": "重坦次数",
                         "ground_battles_spaa": "防空车次数", "time_played_ground_battles": "陆战时长",
                         "tank_battle_time": "坦克时长", "tank_destroyer_battle_time": "坦歼时长",
                         "heavy_tank_battle_time": "重坦时长", "spaa_battle_time": "防空车时长"}
        naval_title = {
            "naval_battles": "海战次数",
            "total_targets_destroyed": "共击毁目标",
            "air_targets_destroyed": "击毁空中目标",
            "ground_targets_destroyed": "击毁地面目标",
            "naval_targets_destroyed": "击毁海上目标",
            "ship_battles": "战舰次数",
            "motor_torpedo_boat_battles": "鱼雷艇次数",
            "motor_gun_boat_battles": "炮艇次数",
            "motor_torpedo_gun_boat_battles": "鱼雷炮艇次数",
            "sub_chaser_battles": "潜艇次数",
            "destroyer_battles": "驱逐舰次数",
            "naval_ferry_barge_battles": "浮船次数",
            "time_played_naval": "海战时长",
            "time_played_on_ship": "战舰时长",
            "time_played_on_motor_torpedo_boat": "鱼雷艇时长",
            "time_played_on_motor_gun_boat": "炮艇时长",
            "time_played_on_motor_torpedo_gun_boat": "鱼雷炮艇时长",
            "time_played_on_sub_chaser": "潜艇时长",
            "time_played_on_destroyer": "驱逐舰时长",
            "time_played_on_naval_ferry_barge": "浮船时长"
        }

        # 娱乐街机
        draw.text((80, 650), f"娱乐街机:", fill="black", font=title_font)
        y = 710
        for key, value in titles.items():
            draw.text((80, y), f"{value}: {data['statistics']['arcade'][key]}", fill="black", font=normal_font)
            y += 37

        # 娱乐街机 - 空战
        draw.text((400, 650), f"街机-空战:", fill="black", font=title_font)
        y = 710
        for key, value in air_titles.items():
            draw.text((400, y), f"{value}: {data['statistics']['arcade']['aviation'][key]}", fill="black",
                      font=normal_font)
            y += 37

        # 娱乐街机 - 陆战
        draw.text((750, 650), f"街机-陆战:", fill="black", font=title_font)
        y = 710
        for key, value in ground_titles.items():
            draw.text((750, y), f"{value}: {data['statistics']['arcade']['ground'][key]}", fill="black",
                      font=normal_font)
            y += 37

        # 娱乐街机 - 海战
        draw.text((1100, 650), f"街机-海战:", fill="black", font=title_font)
        x, y = 1100, 710
        for key, value in naval_title.items():
            draw.text((x, y), f"{value}: {data['statistics']['arcade']['fleet'][key]}", fill="black", font=normal_font)
            y += 37
            if y > 1063:
                x = 1400
                y = 710

        # 历史性能
        draw.text((80, 1250), f"历史性能:", fill="black", font=title_font)
        y = 1310
        for key, value in titles.items():
            draw.text((80, y), f"{value}: {data['statistics']['realistic'][key]}", fill="black", font=normal_font)
            y += 37

        # 历史性能 - 空战
        draw.text((400, 1250), f"空历:", fill="black", font=title_font)
        y = 1310
        for key, value in air_titles.items():
            draw.text((400, y), f"{value}: {data['statistics']['realistic']['aviation'][key]}", fill="black",
                      font=normal_font)
            y += 37

        # 历史性能 - 陆战
        draw.text((750, 1250), f"陆历:", fill="black", font=title_font)
        y = 1310
        for key, value in ground_titles.items():
            draw.text((750, y), f"{value}: {data['statistics']['realistic']['ground'][key]}", fill="black",
                      font=normal_font)
            y += 37

        # 历史性能 - 海战
        draw.text((1100, 1250), f"历史性能-海战:", fill="black", font=title_font)
        x, y = 1100, 1310
        for key, value in naval_title.items():
            draw.text((x, y), f"{value}: {data['statistics']['realistic']['fleet'][key]}", fill="black",
                      font=normal_font)
            y += 37
            if y > 1663:
                x = 1400
                y = 1310

        # 真实模拟
        draw.text((80, 1850), f"真实模拟:", fill="black", font=title_font)
        y = 1910
        for key, value in titles.items():
            draw.text((80, y), f"{value}: {data['statistics']['simulation'][key]}", fill="black", font=normal_font)
            y += 37

        # 真实模拟 - 空战
        draw.text((400, 1850), f"真实模拟-空战:", fill="black", font=title_font)
        y = 1910
        for key, value in air_titles.items():
            draw.text((400, y), f"{value}: {data['statistics']['realistic']['aviation'][key]}", fill="black",
                      font=normal_font)
            y += 37

        # 真实模拟 - 陆战
        draw.text((750, 1850), f"真实模拟-陆战:", fill="black", font=title_font)
        y = 1910
        for key, value in ground_titles.items():
            draw.text((750, y), f"{value}: {data['statistics']['realistic']['ground'][key]}", fill="black",
                      font=normal_font)
            y += 37

        # 真实模拟 - 海战
        draw.text((1100, 1850), f"真实模拟-海战:", fill="black", font=title_font)
        x, y = 1100, 1910
        for key, value in naval_title.items():
            draw.text((x, y), f"{value}: {data['statistics']['realistic']['fleet'][key]}", fill="black",
                      font=normal_font)
            y += 37
            if y > 2263:
                x = 1400
                y = 1910

        byte_array = io.BytesIO()
        img.save(byte_array, "PNG")
        return byte_array.getvalue()

    @staticmethod
    def _download_avatar(url: str) -> Image.Image:
        try:
            # 创建缓存目录
            cache_dir = "resource/images/avatar"
            os.makedirs(cache_dir, exist_ok=True)

            # 使用URL的最后部分作为文件名
            file_path = os.path.join(cache_dir, url.split('/')[-1])

            # 检查缓存
            if os.path.exists(file_path):
                return Image.open(file_path)
            else:
                resp = requests.get(url)
                with open(file_path, "wb") as f:
                    f.write(resp.content)
                return Image.open(file_path)
        except:
            return Image.new("RGBA", (150, 150), (255, 255, 255, 255))

    @staticmethod
    def _show_actual(pct, allvals):
        absolute = int(np.round(pct / 100. * sum(allvals)))  # 将百分比转换为实际值[3][9]
        return f"{absolute}"
