from flask import Blueprint, render_template

from WebUI.utils.auth_utils import login_required

# 创建日志管理蓝图
logs_bp = Blueprint('logs', __name__, url_prefix='/logs')


@logs_bp.route('/')
@login_required
def index():
    """日志管理首页"""
    return render_template('logs/index.html',
                           page_title='日志管理',
                           directory='logs')
