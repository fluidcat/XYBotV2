from flask import Blueprint, render_template, jsonify, current_app

from WebUI.services.tool_service import execute_tool, get_tools_list
from WebUI.utils.auth_utils import login_required

# 创建工具箱蓝图
tools_bp = Blueprint('tools', __name__, url_prefix='/tools')


@tools_bp.route('/')
@login_required
def index():
    """工具箱页面首页"""
    context = {
        'page_title': '工具箱',
    }
    return render_template('tools/index.html', **context)


@tools_bp.route('/api/list')
@login_required
def list_tools():
    """获取工具列表"""
    try:
        tools = get_tools_list()
        return jsonify({
            'code': 0,
            'msg': '获取成功',
            'data': tools
        })
    except Exception as e:
        current_app.logger.error(f"获取工具列表失败: {str(e)}")
        return jsonify({
            'code': 1,
            'msg': f'获取工具列表失败: {str(e)}'
        })


@tools_bp.route('/api/execute/<tool_id>', methods=['POST'])
@login_required
def execute_tool_api(tool_id):
    """执行工具"""
    try:
        # 执行工具
        result = execute_tool(tool_id)

        return jsonify({
            'code': 0,
            'msg': '执行成功',
            'data': result
        })
    except Exception as e:
        error_msg = f"执行工具 {tool_id} 失败: {str(e)}"
        current_app.logger.error(error_msg)

        return jsonify({
            'code': 1,
            'msg': error_msg
        })
