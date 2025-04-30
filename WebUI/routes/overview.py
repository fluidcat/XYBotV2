from flask import Blueprint, render_template, jsonify
import asyncio

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
    try:
        # 获取最新的数据
        data_service._refresh_cache_data()  # 确保数据是最新的
        
        # 获取所有数据
        context = bot_bridge.get_profile()
        metrics = data_service.get_metrics()
        status = bot_service.get_status()
        
        # 确保所有数据是可JSON序列化的
        for k, v in list(metrics.items()):
            if isinstance(v, (asyncio.Task, asyncio.Future)):
                try:
                    # 尝试获取Task的结果
                    loop = asyncio.get_event_loop()
                    if v._state == 'PENDING':
                        metrics[k] = 0  # 如果任务仍在等待，使用默认值
                    else:
                        metrics[k] = str(v)  # 安全转换为字符串
                except Exception:
                    metrics[k] = 0  # 出错时使用默认值
        
        # 确保所有值都是基本数据类型
        for k, v in list(context.items()):
            if not isinstance(v, (str, int, float, bool, type(None))):
                context[k] = str(v)
        
        # 更新上下文
        context.update(metrics)
        context.update(status)
        
        return jsonify(context)
    except Exception as e:
        # 返回错误信息
        return jsonify({
            'error': str(e),
            'status': 'error'
        })
