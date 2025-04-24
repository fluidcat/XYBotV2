import io
import tomllib
from pathlib import Path

import filetype
import requests

from WechatAPI import WechatAPIClient
from plugins.LLMBridge.LLMBridge_config import load_config, conf
from plugins.LLMBridge.bridge.bridge import Bridge
from plugins.LLMBridge.bridge.context import Context, ContextType
from plugins.LLMBridge.bridge.reply import ReplyType
from plugins.LLMBridge.common.const import *
from plugins.LLMBridge.role import Role
from utils.const import PLUGIN_ENDED, PLUGIN_PASS
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
        self.no_at_chat_room = plugin_config["no_at_chat_room"]

        load_config()
        self.bridge = Bridge()
        self.role = Role()

    def check(self, bot: WechatAPIClient, message: dict) -> bool:
        if message["SenderWxid"] in self.admins:  # 自己发送不进行AI回答
            return False
        return True

    async def handle_if_command(self, bot: WechatAPIClient, message: dict):
        """
        不处理 PLUGIN_HANDLED
        """
        if message.get("handled", False):
            return True
        """
        '#'开头的都是指令，若是指令则返回True，否则返回False
        """
        command = message.get('command', '')
        at_bot = message.get('at_bot', False)
        is_command = command.startswith('#')

        # 特殊指令，LLMBridge的Bot内置的指令，当成聊天处理
        if not is_command or command in ['#清除记忆', '#清除所有', '#更新配置']:
            return False

        # 判断是否自身命令
        # if command.split(maxsplit=1)[0].removeprefix('#') not in self.commands:
        #     return is_command

        if message["IsGroup"]:
            message['reply_ats'] = [message["SenderWxid"]]

        if await self.handle_role_play_command(bot, message):
            return is_command

        if await self.handle_model_command(bot, message):
            return is_command

        if await self.handle_openai_compatible_command(bot, message):
            return is_command

        return is_command

    async def handle_openai_compatible_command(self, channel: WechatAPIClient, message: dict):
        cmd = message.get('command').split(maxsplit=1)
        cmd_args = [] if len(cmd) == 1 else cmd[1].split()
        cmd = cmd[0]

        is_cmd = cmd.lower() in ['#openai']
        if not is_cmd:
            return is_cmd
        bridge_conf = conf()

        all_platform = bridge_conf.get("open_ai_compatible")
        all_platform.pop('remark', None)
        help_txt = [f"{key} - {value['desc']}" for key, value in all_platform.items()]
        help_txt = "\n\n可用平台：\n" + "\n".join(help_txt)
        if not cmd_args:
            base = bridge_conf.get("open_ai_api_base")
            platform = next((v for v in all_platform.values() if v["open_ai_api_base"] == base), None)
            desc = '默认' if not platform else platform["desc"]
            await channel.send_reply_message(message,
                                             f'当前openai兼容平台为: {desc}, model为{bridge_conf.get("model")}{help_txt}')
        else:
            platform = cmd_args[0]
            target = all_platform.get(platform)
            if not target:
                await channel.send_reply_message(message, f'openai兼容平台[{platform}]暂不支持{help_txt}')
            else:
                model = target["model"]
                bridge_conf["open_ai_api_base"] = target["open_ai_api_base"]
                bridge_conf["open_ai_api_key"] = target["open_ai_api_key"]
                conf()["model"] = model
                Bridge().reset_bot()
                await channel.send_reply_message(message, f'设置openai兼容平台为: {target["desc"]}, model为{model}')
        return is_cmd

    async def handle_model_command(self, channel: WechatAPIClient, message: dict):
        cmd = message.get('command').split(maxsplit=1)
        cmd_args = [] if len(cmd) == 1 else cmd[1].split()
        cmd = cmd[0]

        is_cmd = cmd in ['#model']
        if not is_cmd:
            return is_cmd

        if not cmd_args:
            await channel.send_reply_message(message, f'当前模型为: {conf().get("model")}')
        else:
            model = self.model_mapping(cmd_args[0])
            if model not in MODEL_LIST:
                await channel.send_reply_message(message, f'模型[{model}]暂不支持')
            else:
                conf()["model"] = self.model_mapping(cmd_args[0])
                Bridge().reset_bot()
                model = conf().get("model") or GPT35
                await channel.send_reply_message(message, f'模型设置为: {model}')
        return is_cmd

    def model_mapping(self, model) -> str:
        if model == GPT4_TURBO:
            return GPT4_TURBO_PREVIEW
        return model

    async def handle_role_play_command(self, bot: WechatAPIClient, message: dict):
        cmd = message.get('command').split(maxsplit=1)[0]
        is_role_cmd = cmd in ['#停止扮演', '#角色', '#role', '#设定扮演', '#角色类型']
        if not is_role_cmd and len(cmd) < 11:
            sim_role = cmd.removeprefix('#')
            is_role_cmd = bool(self.role.get_role(sim_role, min_sim=0.5))
            message['command'] = f"#角色 {sim_role}" if is_role_cmd else message['command']

        if is_role_cmd:
            await self.role.handle_role_play(bot, message, self.generateSessionId(bot, message))
        return is_role_cmd

    @on_text_message(priority=30)
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        # 判断并执行指令
        if await self.handle_if_command(bot, message):
            return
        # 如果是群聊，表示这个消息是没有@机器人的，不处理；有@机器人的是走on_at_message的方法
        query = str(message["Content"]).strip()
        if query == "" \
                or (not message.get('at_bot') and message['Ats']) \
                or (message["IsGroup"] and message["FromWxid"] not in self.no_at_chat_room):
            return

        # 处理角色扮演
        ret = await self.role.handle_role_play(bot, message, self.generateSessionId(bot, message))
        # 只处理角色扮演，其他的文本交给playwright插件
        if ret == "no_role_play":
            return PLUGIN_PASS

        query = str(message["Content"]).strip()
        context = Context(ContextType.TEXT, query)
        context.kwargs = dict()
        context["session_id"] = self.generateSessionId(bot, message)
        reply = self.bridge.fetch_reply_content(query, context)
        await bot.send_reply_message(message, reply.content)

    @on_at_message(priority=20)
    async def handle_at(self, bot: WechatAPIClient, message: dict):
        # 判断并执行指令
        if await self.handle_if_command(bot, message):
            return

        query = str(message["Content"]).strip()
        # 判断有没有@机器人，消息有可能是@其他人
        if not message.get('at_bot', False) or query == "":
            return

        # 处理角色扮演
        ret = await self.role.handle_role_play(bot, message, self.generateSessionId(bot, message))
        # 只处理角色扮演，其他的文本交给playwright插件
        if ret == "no_role_play":
            return PLUGIN_PASS

        query = query.removeprefix(f'@{bot.nickname}\u2005').removesuffix('\u2005').removesuffix(f'@{bot.nickname}')
        context = Context(ContextType.TEXT, query)
        context.kwargs = dict()
        context["session_id"] = self.generateSessionId(bot, message)
        reply = self.bridge.fetch_reply_content(query, context)

        # 回复时@人
        if message["IsGroup"] and message["FromWxid"] not in self.no_at_chat_room:
            message['reply_ats'] = [message["SenderWxid"]]
        await bot.send_reply_message(message, reply.content)

    def generateSessionId(self, bot: WechatAPIClient, message: dict):
        session_id = message.get('FromWxid')
        if message["IsGroup"] and session_id not in self.no_at_chat_room:
            session_id = f"{message.get('FromWxid')}@{message.get('SenderWxid')}"
        return session_id

    # @on_voice_message(priority=20)
    async def handle_voice(self, bot: WechatAPIClient, message: dict):

        # if message["IsGroup"]:
        #     return

        file = io.BytesIO(message['Content'])
        result = self.bridge.fetch_voice_to_text(file)
        if result.type != ReplyType.TEXT or not result.content:
            return False

        message['Content'] = result.content
        message['Ats'] = []
        message['command'] = result.content

        # 处理角色扮演
        await self.role.handle_role_play(bot, message, self.generateSessionId(bot, message))

        query = str(message["Content"]).strip()
        context = Context(ContextType.TEXT, query)
        context.kwargs = dict()
        context["session_id"] = self.generateSessionId(bot, message)
        reply = self.bridge.fetch_reply_content(query, context)

        voice_reply = self.bridge.fetch_text_to_voice(reply.content)
        if voice_reply.type != ReplyType.ERROR and len(voice_reply.content) <= 130:
            voice = voice_reply.content if isinstance(voice_reply.content, bytes) else Path(voice_reply.content)
            await bot.send_voice_message(message['FromWxid'], voice, filetype.guess_extension(voice))
        else:
            await bot.send_reply_message(message, f'我听到：{result.content}\n\n' + reply.content)
        return False

    # @on_image_message(priority=20)
    async def handle_image(self, bot: WechatAPIClient, message: dict):
        if not self.check(bot, message):
            return

        if message["IsGroup"]:
            return

        return False

    # @on_video_message(priority=20)
    async def handle_video(self, bot: WechatAPIClient, message: dict):
        if not self.check(bot, message):
            return

        if message["IsGroup"]:
            return

        return False

    # @on_file_message(priority=20)
    async def handle_file(self, bot: WechatAPIClient, message: dict):
        if not self.check(bot, message):
            return

        if message["IsGroup"]:
            return

        return False
