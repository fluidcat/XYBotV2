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
        self.commands = plugin_config["commands"]

        load_config()
        self.bridge = Bridge()

    def check(self, bot: WechatAPIClient, message: dict) -> bool:
        if not self.enable:
            return False

        command = message.get('command')
        at_bot = message.get('at_bot', False)

        # '#'开头的都是指令，判断是不是这个插件的指令
        if command.startswith('#') and command.removeprefix('#') not in self.commands:
            return False

        # 群聊：不是指令&&没有@机器人，不需要ai回复
        if message["IsGroup"] and not command.startswith('#') and not at_bot:
            return False

        if message["SenderWxid"] in self.admins:  # 自己发送不进行AI回答
            return False

        query = str(message["Content"]).strip()
        if query == "":
            return False

        return True


    @on_text_message(priority=30)
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        if not self.check(bot, message):
            return
        # 群聊走到这里，只有指令
        if message["IsGroup"] and message.get('command') not in ['#清除记忆', '#清除所有', '#更新配置']:
            pass
            return

        # 群聊不会走到这里
        query = str(message["Content"]).strip()
        context = Context(ContextType.TEXT, query)
        context.kwargs = dict()
        context["session_id"] = message.get("FromWxid")
        reply = self.bridge.fetch_reply_content(query, context)
        await bot.send_reply_message(message, reply.content)

    @on_at_message(priority=20)
    async def handle_at(self, bot: WechatAPIClient, message: dict):
        if not self.check(bot, message):
            return
        # 指令
        if message.get('command').startswith('#') and message.get('command') not in ['#清除记忆', '#清除所有', '#更新配置']:
            pass
            return

        query = str(message["Content"]).strip()
        query = query.removeprefix(f'@{bot.nickname}\u2005').removesuffix('\u2005').removesuffix(f'@{bot.nickname}')
        context = Context(ContextType.TEXT, query)
        context.kwargs = dict()
        if message["IsGroup"]:
            context["session_id"] = f"{message.get('FromWxid')}@{message.get('SenderWxid')}"
            message['reply_ats'] = [message["SenderWxid"]]
        else:
            context["session_id"] = message.get('FromWxid')
        reply = self.bridge.fetch_reply_content(query, context)
        await bot.send_reply_message(message, reply.content)

    @on_voice_message(priority=20)
    async def handle_voice(self, bot: WechatAPIClient, message: dict):
        if not self.check(bot, message):
            return

        if message["IsGroup"]:
            return

        return False

    @on_image_message(priority=20)
    async def handle_image(self, bot: WechatAPIClient, message: dict):
        if not self.check(bot, message):
            return

        if message["IsGroup"]:
            return

        return False

    @on_video_message(priority=20)
    async def handle_video(self, bot: WechatAPIClient, message: dict):
        if not self.check(bot, message):
            return

        if message["IsGroup"]:
            return

        return False

    @on_file_message(priority=20)
    async def handle_file(self, bot: WechatAPIClient, message: dict):
        if not self.check(bot, message):
            return

        if message["IsGroup"]:
            return

        return False
