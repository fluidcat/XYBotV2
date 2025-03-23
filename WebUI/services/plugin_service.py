import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

from WebUI.common.bot_bridge import bot_bridge
from WebUI.utils.singleton import Singleton

# 确保可以导入根目录模块
ROOT_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, str(ROOT_DIR))


class PluginService(metaclass=Singleton):
    """插件服务类，提供插件管理功能"""

    def __init__(self):
        """初始化插件服务"""
        # 配置目录
        self.config_dir = ROOT_DIR / 'plugins'

    def get_all_plugins(self) -> List[Dict[str, Any]]:
        return bot_bridge.get_all_plugins()

    def get_plugin_details(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        return bot_bridge.get_plugin_details(plugin_name)

    async def enable_plugin(self, plugin_name: str) -> bool:
        return await bot_bridge.enable_plugin(plugin_name)

    async def disable_plugin(self, plugin_name: str) -> bool:
        return await bot_bridge.disable_plugin(plugin_name)

    async def reload_plugin(self, plugin_name: str) -> bool:
        return await bot_bridge.reload_plugin(plugin_name)


plugin_service = PluginService()
