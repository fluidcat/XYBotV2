import traceback

from flask import Blueprint, request, jsonify, render_template, current_app

from WebUI.services.config_service import config_service
from WebUI.utils.auth_utils import login_required

# 创建蓝图
config_bp = Blueprint('config', __name__, url_prefix='/config')


@config_bp.route('/', methods=['GET'])
@login_required
def configs_page():
    """设置管理页面"""
    current_app.logger.info("访问设置管理页面")
    return render_template('config/index.html')


@config_bp.route('/api/config', methods=['GET'])
@login_required
def get_config():
    """
    获取配置
    
    返回:
        JSON: 配置数据
    """
    try:
        current_app.logger.info("开始获取所有配置")
        config = config_service.get_config()
        current_app.logger.info(f"成功获取配置，包含 {len(config)} 个配置节")

        return jsonify({
            "code": 0,
            "msg": "成功",
            "data": config
        })
    except Exception as e:
        error_detail = traceback.format_exc()
        current_app.logger.error(f"获取配置失败: {str(e)}")
        current_app.logger.error(f"异常详情: {error_detail}")

        return jsonify({
            "code": 500,
            "msg": f"获取配置失败: {str(e)}",
            "error_detail": error_detail
        })


@config_bp.route('/api/schema', methods=['GET'])
@login_required
def get_schema():
    """
    获取表单架构
    
    返回:
        JSON: 表单架构
    """
    try:
        current_app.logger.info("开始获取表单架构")
        schema = config_service.get_form_schema()
        current_app.logger.info(f"成功获取表单架构，包含 {len(schema)} 个配置节")

        return jsonify({
            "code": 0,
            "msg": "成功",
            "data": schema
        })
    except Exception as e:
        error_detail = traceback.format_exc()
        current_app.logger.error(f"获取表单架构失败: {str(e)}")
        current_app.logger.error(f"异常详情: {error_detail}")

        return jsonify({
            "code": 500,
            "msg": f"获取表单架构失败: {str(e)}",
            "error_detail": error_detail
        })


@config_bp.route('/api/schemas', methods=['GET'])
@login_required
def get_schemas():
    """
    获取表单架构（别名）
    
    返回:
        JSON: 表单架构
    """
    current_app.logger.info("转发请求到 /api/schema")
    # 复用get_schema函数的逻辑
    return get_schema()


@config_bp.route('/api/config', methods=['POST'])
@login_required
def save_config():
    """
    保存配置
    
    请求体:
        JSON: 配置数据
        
    返回:
        JSON: 操作结果
    """
    try:
        current_app.logger.info("开始保存所有配置")

        # 获取请求体中的JSON数据
        config_data = request.json
        current_app.logger.info(f"接收到配置数据: {config_data}")

        if not config_data:
            current_app.logger.warning("保存配置失败: 请求数据为空")
            return jsonify({
                "code": 400,
                "msg": "请求数据为空",
                "data": None
            })

        # 验证配置
        current_app.logger.info("验证配置数据")
        valid, errors = config_service.validate_config(config_data)
        if not valid:
            current_app.logger.warning(f"配置验证失败: {errors}")
            return jsonify({
                "code": 400,
                "msg": "配置验证失败",
                "data": errors
            })

        # 保存配置
        current_app.logger.info("开始保存配置到文件")
        result = config_service.save_config(config_data)

        if result:
            current_app.logger.info("配置保存成功")
            return jsonify({
                "code": 0,
                "msg": "配置保存成功",
                "data": None
            })
        else:
            current_app.logger.warning("配置保存失败: 保存操作返回失败")
            return jsonify({
                "code": 500,
                "msg": "配置保存失败",
                "data": None
            })
    except Exception as e:
        error_detail = traceback.format_exc()
        current_app.logger.error(f"保存配置失败: {str(e)}")
        current_app.logger.error(f"异常详情: {error_detail}")

        return jsonify({
            "code": 500,
            "msg": f"保存配置失败: {str(e)}",
            "error_detail": error_detail
        })


@config_bp.route('/api/config/<config_name>', methods=['POST'])
@login_required
def save_specific_config(config_name: str):
    """
    保存特定配置
    
    参数:
        config_name (str): 配置名称
        
    请求体:
        JSON: 配置数据
        
    返回:
        JSON: 操作结果
    """
    try:
        current_app.logger.info(f"开始保存特定配置节: {config_name}")

        # 获取请求体中的JSON数据
        config_data = request.json
        current_app.logger.info(f"接收到配置数据: {config_data}")

        if not config_data:
            current_app.logger.warning(f"保存配置节 {config_name} 失败: 请求数据为空")
            return jsonify({
                "code": 400,
                "msg": "请求数据为空",
                "data": None
            })

        # 创建包含特定配置的完整配置数据结构
        full_config = {config_name: config_data}

        # 验证配置
        current_app.logger.info(f"验证配置节 {config_name} 数据")
        valid, errors = config_service.validate_config(full_config)
        if not valid:
            current_app.logger.warning(f"配置节 {config_name} 验证失败: {errors}")
            return jsonify({
                "code": 400,
                "msg": "配置验证失败",
                "data": errors
            })

        # 保存配置
        current_app.logger.info(f"开始保存配置节 {config_name} 到文件")
        result = config_service.save_config(full_config)

        if result:
            current_app.logger.info(f"配置节 {config_name} 保存成功")
            return jsonify({
                "code": 0,
                "msg": "配置保存成功",
                "data": None
            })
        else:
            current_app.logger.warning(f"配置节 {config_name} 保存失败: 保存操作返回失败")
            return jsonify({
                "code": 500,
                "msg": "配置保存失败",
                "data": None
            })
    except Exception as e:
        error_detail = traceback.format_exc()
        current_app.logger.error(f"保存配置节 {config_name} 失败: {str(e)}")
        current_app.logger.error(f"异常详情: {error_detail}")

        return jsonify({
            "code": 500,
            "msg": f"保存配置失败: {str(e)}",
            "error_detail": error_detail
        })
