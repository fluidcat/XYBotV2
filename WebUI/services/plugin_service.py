import asyncio
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

from loguru import logger

from WebUI.common.bot_bridge import bot_bridge
from WebUI.utils.singleton import Singleton

# 确保可以导入根目录模块
ROOT_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, str(ROOT_DIR))


def get_event_loop():
    """
    获取一个可用的事件循环，如果当前循环已关闭则创建新循环
    
    Returns:
        asyncio.AbstractEventLoop: 事件循环
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            logger.log('WEBUI', f"插件服务: 检测到事件循环已关闭，创建新循环")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop


class PluginService(metaclass=Singleton):
    """插件服务类，提供插件管理功能"""

    def __init__(self):
        """初始化插件服务"""
        # 配置目录
        self.config_dir = ROOT_DIR / 'plugins'
        logger.log('WEBUI', "插件服务初始化完成")

    def get_all_plugins(self) -> List[Dict[str, Any]]:
        """获取所有插件列表"""
        return bot_bridge.get_all_plugins()

    def get_plugin_details(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """获取指定插件的详细信息"""
        return bot_bridge.get_plugin_details(plugin_name)

    async def enable_plugin(self, plugin_name: str) -> bool:
        """启用插件"""
        return await bot_bridge.enable_plugin(plugin_name)

    async def disable_plugin(self, plugin_name: str) -> bool:
        """禁用插件"""
        return await bot_bridge.disable_plugin(plugin_name)

    async def reload_plugin(self, plugin_name: str) -> bool:
        """重新加载插件"""
        return await bot_bridge.reload_plugin(plugin_name)
    
    def run_async(self, coro):
        """
        安全地执行异步协程
        
        Args:
            coro: 协程对象
            
        Returns:
            协程执行结果
        """
        loop = get_event_loop()
        
        if loop.is_running():
            # 如果循环正在运行，使用run_coroutine_threadsafe
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result(timeout=30)  # 设置30秒超时
        else:
            # 否则直接运行
            return loop.run_until_complete(coro)
    
    def save_plugin_config(self, plugin_name: str, config_data: Dict[str, Any]) -> bool:
        """
        保存插件配置
        
        Args:
            plugin_name: 插件名称
            config_data: 配置数据
            
        Returns:
            bool: 保存是否成功
        """
        try:
            # 实现保存插件配置的逻辑
            # 这里是一个占位实现，您需要根据实际情况完善
            logger.log('WEBUI', f"保存插件 {plugin_name} 配置")
            return True
        except Exception as e:
            logger.log('WEBUI', f"保存插件配置失败: {str(e)}")
            return False


plugin_service = PluginService()
