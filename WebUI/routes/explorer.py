from flask import Blueprint, render_template, request

from WebUI.utils.auth_utils import login_required

explorer_bp = Blueprint('explorer', __name__, url_prefix='/explorer')


@explorer_bp.route('/')
@login_required
# 暂时注释掉 @login_required
def index():
    """文件浏览器主页"""
    path = request.args.get('path', '')
    return render_template('explorer/index.html',
                           page_title='文件浏览器',
                           initial_path=path)


@explorer_bp.route('/view/<path:file_path>')
@login_required
# 暂时注释掉 @login_required
def view_file(file_path):
    """查看文件内容"""
    return render_template('explorer/view.html',
                           file_path=file_path,
                           page_title='文件查看')
