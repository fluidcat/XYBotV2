import json
import os
import pathlib
import traceback
from typing import Dict, List, Any, Optional, Callable

from loguru import logger

# 工具注册表
_TOOLS_REGISTRY: Dict[str, Dict[str, Any]] = {}


def register_tool(tool_id: str, title: str, description: str,
                  icon: str, handler_func: Callable, params: Optional[List[Dict[str, Any]]] = None) -> bool:
    """
    注册工具到工具注册表
    
    Args:
        tool_id: 工具ID，唯一标识
        title: 工具标题
        description: 工具描述
        icon: 工具图标(Font Awesome图标名)
        handler_func: 处理函数
        params: 工具参数定义，默认为None
        
    Returns:
        bool: 注册是否成功
        
    Raises:
        ValueError: 当处理函数不可调用时
    """
    if tool_id in _TOOLS_REGISTRY:
        logger.log('WEBUI', f"工具 {tool_id} 已存在，将被覆盖")

    # 检查处理函数是否有效
    if not callable(handler_func):
        error_msg = f"工具 {tool_id} 的处理函数必须是可调用的"
        logger.log('WEBUI', f"注册工具失败: {error_msg}")
        raise ValueError(error_msg)

    # 注册工具
    _TOOLS_REGISTRY[tool_id] = {
        'id': tool_id,
        'title': title,
        'description': description,
        'icon': icon,
        'handler': handler_func,
        'params': params or []
    }

    logger.log('WEBUI', f"工具 {tool_id} 已注册成功")
    return True


def get_tools_list() -> List[Dict[str, Any]]:
    """
    获取所有注册的工具列表（不包含处理函数）
    
    Returns:
        List[Dict[str, Any]]: 工具列表，每个工具包含id、title、description、icon和params
    """
    # 确保工具已加载
    load_built_in_tools()

    # 返回工具列表（不包含处理函数）
    tools = []
    for tool_id, tool in _TOOLS_REGISTRY.items():
        tools.append({
            'id': tool['id'],
            'title': tool['title'],
            'description': tool['description'],
            'icon': tool['icon'],
            'params': tool['params']
        })

    logger.log('WEBUI', f"获取工具列表，共 {len(tools)} 个工具")
    return tools


def execute_tool(tool_id: str) -> Dict[str, Any]:
    """
    执行指定ID的工具
    
    Args:
        tool_id: 工具ID
    
    Returns:
        Dict[str, Any]: 执行结果
        
    Raises:
        ValueError: 当工具不存在时
    """
    # 确保工具已加载
    load_built_in_tools()

    # 检查工具是否存在
    if tool_id not in _TOOLS_REGISTRY:
        error_msg = f"工具 {tool_id} 不存在"
        logger.log('WEBUI', f"执行工具失败: {error_msg}")
        raise ValueError(error_msg)

    tool = _TOOLS_REGISTRY[tool_id]
    handler = tool['handler']

    try:
        logger.log('WEBUI', f"开始执行工具: {tool_id}")
        # 执行工具处理函数
        result = handler()

        # 默认返回格式
        if result is None:
            result = {'success': True}
        elif not isinstance(result, dict):
            result = {'success': True, 'data': result}

        # 确保包含成功标志
        if 'success' not in result:
            result['success'] = True

        logger.log('WEBUI', f"工具 {tool_id} 执行成功")
        return result
    except Exception as e:
        error_msg = f"执行工具 {tool_id} 出错: {str(e)}"
        logger.log('WEBUI', error_msg)
        logger.log('WEBUI', traceback.format_exc())

        return {
            'success': False,
            'error': str(e),
            'stack': traceback.format_exc()
        }


def load_built_in_tools() -> None:
    """
    加载内置工具
    
    该函数会注册所有系统内置的工具。如需添加新工具，请在此处注册。
    """
    # 如果已经加载，则跳过
    if _TOOLS_REGISTRY:
        return

    logger.log('WEBUI', "开始加载内置工具")

    # 注册内置工具
    register_tool(
        tool_id='reset_account',
        title='登录新账号',
        description='删除当前保存的账号文件，以登录新账号',
        icon='user-plus',
        handler_func=reset_account_handler
    )

    # 可以在这里注册更多内置工具

    logger.log('WEBUI', f"内置工具加载完成，共 {len(_TOOLS_REGISTRY)} 个工具")


def reset_account_handler() -> Dict[str, Any]:
    """
    重置账号文件处理函数
    
    删除现有账号信息，创建一个新的空账号文件，用于重新登录
        
    Returns:
        Dict[str, Any]: 执行结果
    """
    try:
        # 账号文件路径
        account_path = pathlib.Path("resource/robot_stat.json")

        # 检查文件是否存在
        if not os.path.exists(account_path):
            error_msg = '账号文件不存在'
            logger.log('WEBUI', f"重置账号失败: {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }

        # 创建新的账号数据
        new_data = {
            "wxid": "",
            "device_name": "",
            "device_id": ""
        }

        # 写入文件
        with open(account_path, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, ensure_ascii=False, indent=4)

        logger.log('WEBUI', "账号文件已成功重置")
        return {
            'success': True,
            'message': '账号文件已重置'
        }
    except Exception as e:
        error_msg = f"重置账号文件失败: {str(e)}"
        logger.log('WEBUI', error_msg)
        logger.log('WEBUI', traceback.format_exc())
        return {
            'success': False,
            'error': error_msg
        }
