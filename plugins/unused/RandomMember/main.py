import random
import tomllib

from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.plugin_base import PluginBase


class RandomMember(PluginBase):
    description = "随机群成员"
    author = "HenryXiaoYang"
    version = "1.0.0"

    def __init__(self):
        super().__init__()

        with open("plugins/RandomMember/config.toml", "rb") as f:
            plugin_config = tomllib.load(f)

        config = plugin_config["RandomMember"]

        self.enable = config["enable"]
        self.command = config["command"]
        self.count = config["count"]

    @on_text_message
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return

        content = str(message["Content"]).strip()
        command = content.split(" ")

        if command[0] not in self.command:
            return

        if not message["IsGroup"]:
            await bot.send_text_message(message["FromWxid"], "😠只能在群里使用！")
            return

        memlist = await bot.get_chatroom_member_list(message["FromWxid"])
        random_members = random.sample(memlist, self.count)

        output = "\n👋嘿嘿，我随机选到了这几位："
        for member in random_members:
            output += f"\n✨{member['NickName']}"

        await bot.send_at_message(message["FromWxid"], output, [message["SenderWxid"]])
