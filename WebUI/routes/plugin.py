from flask import Blueprint, request, jsonify, render_template
from loguru import logger

from WebUI.services.plugin_service import plugin_service
from WebUI.utils.auth_utils import login_required

# 创建蓝图
plugin_bp = Blueprint('plugin', __name__, url_prefix='/plugin')


@plugin_bp.route('/', methods=['GET'])
@login_required
def plugin_page():
    """插件管理页面"""
    return render_template('plugin/index.html')


@plugin_bp.route('/api/list', methods=['GET'])
@login_required
def get_plugins():
    """
    获取所有插件列表
    
    返回:
        JSON: 所有插件信息列表
    """
    try:
        plugins = plugin_service.get_all_plugins()
        logger.log("WEBUI", f"成功获取到 {len(plugins)} 个插件")
        return jsonify({
            "code": 0,
            "msg": "成功",
            "data": plugins
        })
    except Exception as e:
        logger.log("WEBUI", f"获取插件列表失败: {str(e)}")
        return jsonify({
            "code": 500,
            "msg": f"获取插件列表失败: {str(e)}",
            "data": []
        })


@plugin_bp.route('/api/detail/<plugin_name>', methods=['GET'])
@login_required
def get_plugin_detail(plugin_name: str):
    """
    获取插件详情
    
    参数:
        plugin_name (str): 插件ID
        
    返回:
        JSON: 插件详细信息
    """
    plugin = plugin_service.get_plugin_details(plugin_name)
    if not plugin:
        return jsonify({
            "code": 404,
            "msg": "插件不存在",
            "data": None
        })

    return jsonify({
        "code": 0,
        "msg": "成功",
        "data": plugin
    })


@plugin_bp.route('/api/enable/<plugin_name>', methods=['POST'])
@login_required
def enable_plugin(plugin_name: str):
    """
    启用插件
    
    参数:
        plugin_name (str): 插件ID
        
    返回:
        JSON: 操作结果
    """
    try:
        # 使用run_async执行异步操作，而不是直接用asyncio.run
        result = plugin_service.run_async(plugin_service.enable_plugin(plugin_name))
        
        if result:
            return jsonify({
                "code": 0,
                "msg": "插件启用成功",
                "data": None
            })
        else:
            return jsonify({
                "code": 500,
                "msg": "插件启用失败",
                "data": None
            })
    except Exception as e:
        logger.log("WEBUI", f"启用插件失败: {str(e)}")
        return jsonify({
            "code": 500,
            "msg": f"启用插件失败: {str(e)}",
            "data": None
        })


@plugin_bp.route('/api/disable/<plugin_name>', methods=['POST'])
@login_required
def disable_plugin(plugin_name: str):
    """
    禁用插件
    
    参数:
        plugin_name (str): 插件ID
        
    返回:
        JSON: 操作结果
    """
    try:
        # 使用run_async执行异步操作
        result = plugin_service.run_async(plugin_service.disable_plugin(plugin_name))
        
        if result:
            return jsonify({
                "code": 0,
                "msg": "插件禁用成功",
                "data": None
            })
        else:
            return jsonify({
                "code": 500,
                "msg": "插件禁用失败",
                "data": None
            })
    except Exception as e:
        logger.log("WEBUI", f"禁用插件失败: {str(e)}")
        return jsonify({
            "code": 500,
            "msg": f"禁用插件失败: {str(e)}",
            "data": None
        })


@plugin_bp.route('/api/reload/<plugin_name>', methods=['POST'])
@login_required
def reload_plugin(plugin_name: str):
    """
    重新加载插件
    
    参数:
        plugin_name (str): 插件ID
        
    返回:
        JSON: 操作结果
    """
    try:
        # 使用run_async执行异步操作
        result = plugin_service.run_async(plugin_service.reload_plugin(plugin_name))
        
        if result:
            return jsonify({
                "code": 0,
                "msg": "插件重新加载成功",
                "data": None
            })
        else:
            return jsonify({
                "code": 500,
                "msg": "插件重新加载失败",
                "data": None
            })
    except Exception as e:
        logger.log("WEBUI", f"重载插件失败: {str(e)}")
        return jsonify({
            "code": 500,
            "msg": f"重载插件失败: {str(e)}",
            "data": None
        })


@plugin_bp.route('/api/config/<plugin_name>/list', methods=['GET'])
@login_required
def pluginl_list_files(plugin_name: str):
    """
    获取插件配置
    
    参数:
        plugin_name (str): 插件ID
        
    返回:
        JSON: 插件配置
    """
    root_key = request.args.get('root', 'logs')


@plugin_bp.route('/api/config/<plugin_name>', methods=['POST'])
@login_required
def save_plugin_config(plugin_name: str):
    """
    保存插件配置
    
    参数:
        plugin_name (str): 插件ID
        
    请求体:
        JSON: 插件配置
        
    返回:
        JSON: 操作结果
    """
    # 获取请求体中的JSON数据
    config_data = request.json

    if not config_data:
        return jsonify({
            "code": 400,
            "msg": "请求数据为空",
            "data": None
        })

    # 保存配置
    result = plugin_service.save_plugin_config(plugin_name, config_data)

    if result:
        # 重载插件以应用新配置
        try:
            logger.info(f"正在重载插件 {plugin_name} 以应用新配置...")
            reload_result = plugin_service.run_async(plugin_service.reload_plugin(plugin_name))
            
            if reload_result:
                logger.info(f"插件 {plugin_name} 重载成功")
            else:
                logger.warning(f"插件 {plugin_name} 重载失败")
                
            return jsonify({
                "code": 0,
                "msg": "配置保存成功",
                "data": None
            })
        except Exception as e:
            logger.error(f"插件重载失败: {str(e)}")
            return jsonify({
                "code": 0,
                "msg": "配置已保存，但插件重载失败",
                "data": None
            })
    else:
        return jsonify({
            "code": 500,
            "msg": "配置保存失败",
            "data": None
        })
