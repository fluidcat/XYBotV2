import tomllib

from tabulate import tabulate

from WechatAPI import WechatAPIClient
from database.XYBotDB import XYBotDB
from utils.decorators import *
from utils.plugin_base import PluginBase
from utils.plugin_manager import PluginManager


class ManagePlugin(PluginBase):
    description = "插件管理器"
    author = "HenryXiaoYang"
    version = "1.0.0"

    def __init__(self):
        super().__init__()

        self.db = XYBotDB()

        with open("plugins/ManagePlugin/config.toml", "rb") as f:
            plugin_config = tomllib.load(f)

        with open("main_config.toml", "rb") as f:
            main_config = tomllib.load(f)

        plugin_config = plugin_config["ManagePlugin"]
        main_config = main_config["XYBot"]

        self.command = plugin_config["command"]
        self.admins = main_config["admins"]

        self.plugin_manager = PluginManager()

    @on_text_message
    @on_text_message(priority=90)
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        content = str(message["Content"]).strip()
        command = content.split(" ")

        if not len(command) or command[0] not in self.command:
            return

        if message["SenderWxid"] not in self.admins:
            await bot.send_text_message(message["FromWxid"], "你没有权限使用此命令")
            return

        plugin_name = command[1] if len(command) > 1 else None
        if command[0] == "加载插件":
            if plugin_name in self.plugin_manager.plugins.keys():
                await bot.send_text_message(message["FromWxid"], "⚠️插件已经加载")
                return

            attempt = await self.plugin_manager.load_plugin(plugin_name)
            if attempt:
                await bot.send_text_message(message["FromWxid"], f"✅插件 {plugin_name} 加载成功")
            else:
                await bot.send_text_message(message["FromWxid"], f"❌插件 {plugin_name} 加载失败，请查看日志错误信息")

        elif command[0] == "加载所有插件":
            attempt = await self.plugin_manager.load_plugins(load_disabled=True)
            if isinstance(attempt, list):
                attempt = '\n'.join(attempt)
                await bot.send_text_message(message["FromWxid"], f"✅插件加载成功：\n{attempt}")
            else:
                await bot.send_text_message(message["FromWxid"], "❌插件加载失败，请查看日志错误信息")

        elif command[0] == "卸载插件":
            if plugin_name == "ManagePlugin":
                await bot.send_text_message(message["FromWxid"], "⚠️你不能卸载 ManagePlugin 插件！")
                return
            elif plugin_name not in self.plugin_manager.plugins.keys():
                await bot.send_text_message(message["FromWxid"], "⚠️插件不存在或未加载")
                return

            attempt = await self.plugin_manager.unload_plugin(plugin_name)
            if attempt:
                await bot.send_text_message(message["FromWxid"], f"✅插件 {plugin_name} 卸载成功")
            else:
                await bot.send_text_message(message["FromWxid"], f"❌插件 {plugin_name} 卸载失败，请查看日志错误信息")

        elif command[0] == "卸载所有插件":
            unloaded_plugins, failed_unloads = await self.plugin_manager.unload_plugins()
            unloaded_plugins = '\n'.join(unloaded_plugins)
            failed_unloads = '\n'.join(failed_unloads)
            await bot.send_text_message(message["FromWxid"],
                                        f"✅插件卸载成功：\n{unloaded_plugins}\n❌插件卸载失败：\n{failed_unloads}")

        elif command[0] == "重载插件":
            if plugin_name == "ManagePlugin":
                await bot.send_text_message(message["FromWxid"], "⚠️你不能重载 ManagePlugin 插件！")
                return
            elif plugin_name not in self.plugin_manager.plugins.keys():
                await bot.send_text_message(message["FromWxid"], "⚠️插件不存在或未加载")
                return

            attempt = await self.plugin_manager.reload_plugin(plugin_name)
            if attempt:
                await bot.send_text_message(message["FromWxid"], f"✅插件 {plugin_name} 重载成功")
            else:
                await bot.send_text_message(message["FromWxid"], f"❌插件 {plugin_name} 重载失败，请查看日志错误信息")

        elif command[0] == "重载所有插件":
            attempt = await self.plugin_manager.reload_plugins()
            if attempt:
                await bot.send_text_message(message["FromWxid"], "✅所有插件重载成功")
            else:
                await bot.send_text_message(message["FromWxid"], "❌插件重载失败，请查看日志错误信息")

        elif command[0] == "插件列表":
            plugin_list = self.plugin_manager.get_plugin_info()

            plugin_stat = [["插件名称", "是否启用"]]
            for plugin in plugin_list:
                plugin_stat.append([plugin['name'], "✅" if plugin['enabled'] else "🚫"])

            table = str(tabulate(plugin_stat, headers="firstrow", tablefmt="simple"))

            await bot.send_text_message(message["FromWxid"], table)

        elif command[0] == "插件信息":
            attemt = self.plugin_manager.get_plugin_info(plugin_name)
            if isinstance(attemt, dict):
                output = (f"插件名称: {attemt['name']}\n"
                          f"插件描述: {attemt['description']}\n"
                          f"插件作者: {attemt['author']}\n"
                          f"插件版本: {attemt['version']}")

                await bot.send_text_message(message["FromWxid"], output)
            else:
                await bot.send_text_message(message["FromWxid"], "⚠️插件不存在或未加载")
