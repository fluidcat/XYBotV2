from flask import Blueprint, render_template, jsonify

from WebUI.common.bot_bridge import bot_bridge
from WebUI.services.bot_service import bot_service
from WebUI.services.data_service import data_service
from WebUI.utils.auth_utils import login_required

# 创建概览蓝图
overview_bp = Blueprint('overview', __name__, url_prefix='/overview')


@overview_bp.route('/')
@login_required
def index():
    """概览页面首页"""
    # 获取初始数据
    bot_status = bot_service.get_status()
    metrics = data_service.get_metrics()

    context = {
        'page_title': '概览',
        'bot_status': bot_status,
        'metrics': metrics,
        'status': 'running' if bot_status.get('running', False) else 'stopped'
    }

    return render_template('overview/index.html', **context)


@overview_bp.route('/api/status')
@login_required
def api_status():
    """获取机器人状态API"""
    context = bot_bridge.get_profile()
    context.update(data_service.get_metrics())
    context.update(bot_service.get_status())
    return jsonify(context)
