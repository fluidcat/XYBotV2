import tomllib

import aiohttp

from WechatAPI import WechatAPIClient
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

        if command[0] not in self.command:
            return

        if len(command) == 1:
            await bot.send_at_message(message["FromWxid"], f"❌命令格式错误！{self.command_format}",
                                      [message["SenderWxid"]])
            return

        song_name = content[len(command[0]):].strip()

        async with aiohttp.ClientSession() as session:
            async with session.get(
                    f"https://www.hhlqilongzhu.cn/api/dg_wyymusic.php?gm={song_name}&n=1&br=2&type=json") as resp:
                data = await resp.json()

        if data["code"] != 200:
            await bot.send_at_message(message["FromWxid"], f"❌点歌失败！\n{data}",
                                      [message["SenderWxid"]])
            return
        title = data["title"]
        singer = data["singer"]
        url = data["link"]
        music_url = data["music_url"].split("?")[0]
        cover_url = data["cover"]
        lyric = data["lrc"]

        xml = f"""<appmsg appid="wx79f2c4418704b4f8" sdkver="0"><title>{title}</title><des>{singer}</des><action>view</action><type>3</type><showtype>0</showtype><content/><url>{url}</url><dataurl>{music_url}</dataurl><lowurl>{url}</lowurl><lowdataurl>{music_url}</lowdataurl><recorditem/><thumburl>{cover_url}</thumburl><messageaction/><laninfo/><extinfo/><sourceusername/><sourcedisplayname/><songlyric>{lyric}</songlyric><commenturl/><appattach><totallen>0</totallen><attachid/><emoticonmd5/><fileext/><aeskey/></appattach><webviewshared><publisherId/><publisherReqId>0</publisherReqId></webviewshared><weappinfo><pagepath/><username/><appid/><appservicetype>0</appservicetype></weappinfo><websearch/><songalbumurl>{cover_url}</songalbumurl></appmsg><fromusername>{bot.wxid}</fromusername><scene>0</scene><appinfo><version>1</version><appname/></appinfo><commenturl/>"""
        await bot.send_app_message(message["FromWxid"], xml, 3)
