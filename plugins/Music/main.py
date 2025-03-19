import re
import tomllib

import aiohttp
import requests

from WechatAPI import WechatAPIClient
from utils.const import *
from utils.decorators import *
from utils.plugin_base import PluginBase


class Music(PluginBase):
    description = "点歌"
    author = "HenryXiaoYang"
    version = "1.0.0"

    def __init__(self):
        super().__init__()

        with open("plugins/Music/config.toml", "rb") as f:
            plugin_config = tomllib.load(f)

        config = plugin_config["Music"]

        self.enable = config["enable"]
        self.command = config["command"]
        self.command_format = config["command-format"]

    @on_text_message
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return

        content = str(message["Content"]).strip()
        command = content.split(" ")
        message['reply_ats'] = [message["SenderWxid"]] if message['IsGroup'] else []

        if command[0] not in self.command:
            return PLUGIN_PASS

        if len(command) == 1:
            await bot.send_reply_message(message, f"{self.command_format}")
            return PLUGIN_ENDED

        song_name = content[len(command[0]):].strip()

        data = await self.get_music_guigui(song_name)

        if data["code"] != 200:
            await bot.send_reply_message(message, f"❌点歌失败！\n{data}")
            return PLUGIN_ENDED

        title = data["title"]
        singer = data["singer"]
        url = data["link"]
        music_url = data["music_url"].split("?")[0]
        cover_url = data["cover"]
        lyric = data["lrc"]

        xml = f"""<appmsg appid="wx485a97c844086dc9" sdkver="0"><title>{title}</title><des>{singer}</des>
        <action>view</action><type>3</type><showtype>0</showtype><content/><url>{url}</url><dataurl>{music_url}</dataurl>
        <lowurl>{url}</lowurl><lowdataurl>{music_url}</lowdataurl><recorditem/><thumburl>{cover_url}</thumburl>
        <messageaction/><laninfo/><extinfo/><sourceusername/><sourcedisplayname/><songlyric>{lyric}</songlyric>
        <commenturl/><appattach><totallen>0</totallen><attachid/><emoticonmd5/><fileext/><aeskey/></appattach>
        <webviewshared><publisherId/><publisherReqId>0</publisherReqId></webviewshared><weappinfo><pagepath/><username/>
        <appid/><appservicetype>0</appservicetype></weappinfo><websearch/><songalbumurl>{cover_url}</songalbumurl>
        </appmsg><fromusername>{bot.wxid}</fromusername><scene>0</scene><appinfo><version>1</version><appname/>
        </appinfo><commenturl/>"""
        await bot.send_app_message(message["FromWxid"], xml, 3)
        return PLUGIN_ENDED

    async def get_music_longzhu(self, song_name):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                    f"https://www.hhlqilongzhu.cn/api/dg_wyymusic.php?gm={song_name}&n=1&br=2&type=json") as resp:
                    # f"http://www.hhlqilongzhu.cn/api/joox/juhe_music.php?msg={song_name}&n=1&type=json") as resp:
                data = await resp.json()
        return data

    async def get_music_guigui(self, song_name):
        match = re.search(r'\d+$', song_name)
        song_name, index = (song_name[:match.start()].strip(), int(match.group())-1) if match else (song_name, 0)
        music = {"code": 0}
        header = {
            "accept": '*/*',
            "accept-language": 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            "priority": 'u=1, i',
            "referer": 'https://cenguigui.cn/music/',
            "sec-ch-ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
            "sec-ch-ua-mobile": '?0',
            "sec-ch-ua-platform": 'Windows',
            "sec-fetch-dest": 'empty',
            "sec-fetch-mode": 'cors',
            "sec-fetch-site": 'same-origin',
            "user-agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/133.0.0.0 Safari/537.36',
            "Connection": 'Keep-Alive',
            "Accept-Encoding": 'br,deflate,gzip,x-gzip',
        }
        list_resp = requests.get(f"https://cenguigui.cn/api/api.php?kw=&msg={song_name}&pn=1", headers=header).json()
        if list_resp.get('code', 0) != 200 or not list_resp.get('data', []):
            return music

        song = list_resp.get('data')[index if len(list_resp.get('data')) > index else -1]
        # 获取歌曲url

        url = requests.get(f"https://cenguigui.cn/api/api.php?kw=&rid={song.get('rid', 0)}", headers=header).text
        if not url:
            return music

        lrc = ''
        lrc_resp = requests.get(f"https://cenguigui.cn/api/api.php?kw=&lrc={song.get('rid', 0)}", headers=header).json()
        if lrc_resp:
            for item in lrc_resp:
                s = float(item['time'])
                mm_ss = f"{int((s % 3600) // 60):02d}:{s % 60:06.3f}"
                lrc += f"[{mm_ss}]{item['lineLyric']}\n"

        music['code'] = 200
        music['link'] = ""
        music['music_url'] = url
        music['title'] = song.get('name')
        music['singer'] = song.get('artist')
        music['cover'] = song.get('pic')
        music['lrc'] = lrc

        return music


