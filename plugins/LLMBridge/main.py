import tomllib

from WechatAPI import WechatAPIClient
from plugins.LLMBridge.LLMBridge_config import load_config
from plugins.LLMBridge.bridge.bridge import Bridge
from plugins.LLMBridge.bridge.context import Context, ContextType
from utils.decorators import *
from utils.plugin_base import PluginBase


class LLMBridge(PluginBase):
    description = "LLM聚合接入"
    author = "fluidcat"
    version = "1.0.0"

    def __init__(self):
        super().__init__()

        with open("main_config.toml", "rb") as f:
            config = tomllib.load(f)

        self.admins = config["XYBot"]["admins"]

        with open("plugins/LLMBridge/config.toml", "rb") as f:
            config = tomllib.load(f)

        plugin_config = config["LLMBridge"]
        self.enable = plugin_config["enable"]
        self.other_plugin_cmd = plugin_config["other-plugin-cmd"]

        load_config()
        self.bridge = Bridge()

    def check(self, bot: WechatAPIClient, message: dict) -> bool:
        command = str(message["Content"]).strip().split(" ")

        if command and command[0] in self.other_plugin_cmd:  # 指令来自其他插件
            return False

        if message["SenderWxid"] in self.admins:  # 自己发送不进行AI回答
            return False

        query = str(message["Content"]).strip()
        if query == "":
            return False

        return True


    @on_text_message(priority=30)
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        if not self.enable and not self.check(bot, message):
            return

        query = str(message["Content"]).strip()
        context = Context(ContextType.TEXT, query)
        context.kwargs = dict()
        context["session_id"] = message.get("FromWxid")
        reply = self.bridge.fetch_reply_content(query, context)
        await bot.send_text_message(message.get("FromWxid"), reply.content)

    @on_at_message(priority=20)
    async def handle_at(self, bot: WechatAPIClient, message: dict):
        if not self.enable and not self.check(bot, message):
            return

        query = str(message["Content"]).strip()
        context = Context(ContextType.TEXT, query)
        context.kwargs = dict()
        context["session_id"] = message.get("FromWxid")
        reply = self.bridge.fetch_reply_content(query, context)
        await bot.send_text_message(message.get("FromWxid"), reply.content)

    @on_voice_message(priority=20)
    async def handle_voice(self, bot: WechatAPIClient, message: dict):
        if not self.enable and not self.check(bot, message):
            return

        if message["IsGroup"]:
            return

        return False

    @on_image_message(priority=20)
    async def handle_image(self, bot: WechatAPIClient, message: dict):
        if not self.enable and not self.check(bot, message):
            return

        if message["IsGroup"]:
            return

        return False

    @on_video_message(priority=20)
    async def handle_video(self, bot: WechatAPIClient, message: dict):
        if not self.enable and not self.check(bot, message):
            return

        if message["IsGroup"]:
            return

        return False

    @on_file_message(priority=20)
    async def handle_file(self, bot: WechatAPIClient, message: dict):
        if not self.enable and not self.check(bot, message):
            return

        if message["IsGroup"]:
            return

        return False
