from flask import Blueprint, jsonify

from WebUI.services.bot_service import bot_service
from WebUI.utils.auth_utils import login_required

bot_bp = Blueprint('bot', __name__, url_prefix='/bot')


@bot_bp.route('/api/start', methods=['POST'])
@login_required
def api_start_bot():
    """启动机器人API"""
    success = bot_service.start_bot()
    return jsonify({
        'success': success,
        'message': '机器人启动成功' if success else '机器人启动失败'
    })


@bot_bp.route('/api/stop', methods=['POST'])
@login_required
def api_stop_bot():
    """停止机器人API"""
    success = bot_service.stop_bot()
    return jsonify({
        'success': success,
        'message': '机器人停止成功' if success else '机器人停止失败'
    })


@bot_bp.route('/api/status', methods=['GET'])
@login_required
def api_get_bot_status():
    """获取机器人状态API"""
    status = bot_service.get_status()
    return jsonify(status)
