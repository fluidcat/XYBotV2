import tomllib

import aiohttp
import jieba

from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.plugin_base import PluginBase
from datetime import datetime


class GetWeather(PluginBase):
    description = "获取天气"
    author = "HenryXiaoYang"
    version = "1.0.1"

    # Change Log
    # 1.0.1 2025-02-20 修改天气插件触发条件

    def __init__(self):
        super().__init__()

        with open("plugins/GetWeather/config.toml", "rb") as f:
            plugin_config = tomllib.load(f)

        config = plugin_config["GetWeather"]

        self.enable = config["enable"]
        self.command_format = config["command-format"]
        self.api_key = config["api-key"]

    @on_text_message
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        return await self.handle(bot, message)

    @on_at_message
    async def handle_at_text(self, bot: WechatAPIClient, message: dict):
        no_at_bot = bot.wxid not in message["Ats"]
        if no_at_bot:
            return
        command = message.get('command')

        if not command.startswith("#") and "天气" in command:
            command = '#' + command

        message['command'] = command
        return await self.handle(bot, message)

    async def handle(self, bot: WechatAPIClient, message: dict):
        command = message.get('command')
        if not command.startswith("#") or "天气" not in command:
            return

        command = command.removeprefix('#').replace(" ", "")
        command = list(jieba.cut(command))

        if message['IsGroup']:
            message['reply_ats'] = [message["SenderWxid"]]

        if len(command) == 1:
            await bot.send_reply_message(message, self.command_format)
            return
        elif len(command) > 3:
            return

        # 配置密钥检查
        if not self.api_key:
            await bot.send_reply_message(message, '你还没配置天气API密钥')
            return

        command.remove("天气")
        request_loc = "".join(command)

        conn_ssl = aiohttp.TCPConnector(ssl=False)
        session = aiohttp.ClientSession(connector=conn_ssl)

        geo_api_url = f'https://geoapi.qweather.com/v2/city/lookup?key={self.api_key}&number=1&location={request_loc}'
        async with session.get(geo_api_url) as response:
            geoapi_json = await response.json()

        if geoapi_json.get('code') == '404':
            await bot.send_reply_message(message, "⚠️查无此地！")
            return
        elif geoapi_json.get('code') != '200':
            await bot.send_reply_message(message, "⚠️请求失败\n{geoapi_json}")
            return

        country = geoapi_json["location"][0]["country"]
        adm1 = geoapi_json["location"][0]["adm1"]
        adm2 = geoapi_json["location"][0]["adm2"]
        city_id = geoapi_json["location"][0]["id"]
        # 请求现在天气api
        now_weather_api_url = f'https://devapi.qweather.com/v7/weather/now?key={self.api_key}&location={city_id}'
        async with session.get(now_weather_api_url) as response:
            now_weather_api_json = await response.json()

        # 请求预报天气api
        weather_forecast_api_url = f'https://devapi.qweather.com/v7/weather/7d?key={self.api_key}&location={city_id}'
        async with session.get(weather_forecast_api_url) as response:
            weather_forecast_api_json = await response.json()

        out_message = self.compose_weather_message(country, adm1, adm2, now_weather_api_json, weather_forecast_api_json)
        await bot.send_reply_message(message, out_message)
        await session.close()
        await conn_ssl.close()

    @staticmethod
    def compose_weather_message(country, adm1, adm2, now_weather_api_json, weather_forecast_api_json):
        update_time = now_weather_api_json['updateTime']
        try:
            update_time = datetime.fromisoformat(update_time).strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            update_time = now_weather_api_json['updateTime']

        now_temperature = now_weather_api_json['now']['temp']
        now_feelslike = now_weather_api_json['now']['feelsLike']
        now_weather = now_weather_api_json['now']['text']
        now_wind_direction = now_weather_api_json['now']['windDir']
        now_wind_scale = now_weather_api_json['now']['windScale']
        now_humidity = now_weather_api_json['now']['humidity']
        now_precip = now_weather_api_json['now']['precip']
        now_visibility = now_weather_api_json['now']['vis']
        now_uvindex = weather_forecast_api_json['daily'][0]['uvIndex']
        max_len = 6

        message = (
            f"☁️{country}{adm1}{adm2} 实时天气☁️\n"
            f"⏰更新时间：{update_time}\n\n"
            f"🌡️ {'当前温度： ':　<{max_len}}　{now_temperature}℃\n"
            f"🌡️ {'体感温度： ':　<{max_len}}　{now_feelslike}℃\n"
            f"☁️{'天气：':　<{max_len}}{now_weather}\n"
            f"☀️{'紫外线指数：':　<{max_len}}{now_uvindex}\n"
            f"🌬️{'风向：':　<{max_len}}{now_wind_direction}\n"
            f"🌬️{'风力：':　<{max_len}}{now_wind_scale}级\n"
            f"💦{'湿度：':　<{max_len}}{now_humidity}%\n"
            f"🌧️{'降水量：':　<{max_len}}{now_precip}mm/h\n"
            f"👀{'能见度：':　<{max_len}}{now_visibility}km\n\n"
            f"☁️未来3天 {adm2} 天气：\n"
        )
        for day in weather_forecast_api_json['daily'][1:4]:
            date = '.'.join([i.lstrip('0') for i in day['fxDate'].split('-')[1:]])
            weather = day['textDay']
            max_temp = day['tempMax']
            min_temp = day['tempMin']
            uv_index = day['uvIndex']
            message += f'{date} {weather} 最高🌡️{max_temp}℃ 最低🌡️{min_temp}℃ ☀️紫外线:{uv_index}\n'

        return message
