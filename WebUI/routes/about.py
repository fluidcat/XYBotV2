from flask import Blueprint, render_template

from WebUI.utils.auth_utils import login_required

about_bp = Blueprint('about', __name__)


@about_bp.route('/about')
@login_required
def about():
    """关于页面路由"""
    return render_template('about/index.html')
