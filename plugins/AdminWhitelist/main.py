import tomllib

from WechatAPI import WechatAPIClient
from database.XYBotDB import XYBotDB
from utils.decorators import *
from utils.plugin_base import PluginBase


class AdminWhitelist(PluginBase):
    description = "管理白名单"
    author = "HenryXiaoYang"
    version = "1.0.0"

    def __init__(self):
        super().__init__()

        with open("plugins/AdminWhitelist/config.toml", "rb") as f:
            plugin_config = tomllib.load(f)

        with open("main_config.toml", "rb") as f:
            main_config = tomllib.load(f)

        config = plugin_config["AdminWhitelist"]
        main_config = main_config["XYBot"]

        self.enable = config["enable"]
        self.command_format = config["command-format"]

        self.admins = main_config["admins"]

        self.db = XYBotDB()

    @on_text_message
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        if not self.enable:
            return

        content = str(message["Content"]).strip()
        command = content.split(" ")

        if not len(command) or command[0] not in ["添加白名单", "移除白名单", "白名单列表"]:
            return

        sender_wxid = message["SenderWxid"]

        if sender_wxid not in self.admins:
            await bot.send_text_message(message["FromWxid"], "❌你配用这个指令吗？😡")
            return

        if command[0] == "添加白名单":
            if len(command) < 2:
                await bot.send_text_message(message["FromWxid"], self.command_format)
                return

            if command[1].startswith("@") and len(message["Ats"]) == 1:  # 判断是@还是wxid
                change_wxid = message["Ats"][0]
            elif "@" not in " ".join(command[1:]):
                change_wxid = command[1]
            else:
                await bot.send_text_message(message["FromWxid"], "❌请不要手动@！")
                return

            self.db.set_whitelist(change_wxid, True)

            nickname = await bot.get_nickname(change_wxid)
            await bot.send_text_message(message["FromWxid"],
                                        f"成功添加 {nickname if nickname else ''} {change_wxid} 到白名单")

        elif command[0] == "移除白名单":
            if len(command) < 2:
                await bot.send_text_message(message["FromWxid"], self.command_format)
                return

            if command[1].startswith("@") and len(message["Ats"]) == 1:  # 判断是@还是wxid
                change_wxid = message["Ats"][0]
            elif "@" not in " ".join(command[1:]):
                change_wxid = command[1]
            else:
                await bot.send_text_message(message["FromWxid"], "❌请不要手动@！")
                return

            self.db.set_whitelist(change_wxid, False)

            nickname = await bot.get_nickname(change_wxid)
            await bot.send_text_message(message["FromWxid"],
                                        f"成功把 {nickname if nickname else ''} {change_wxid} 移出白名单！")

        elif command[0] == "白名单列表":
            whitelist = self.db.get_whitelist_list()
            whitelist = "\n".join([f"{wxid} {await bot.get_nickname(wxid)}" for wxid in whitelist])
            await bot.send_text_message(message["FromWxid"], f"白名单列表：\n{whitelist}")

        else:
            await bot.send_text_message(message["FromWxid"], self.command_format)
            return
