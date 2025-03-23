import functools

from flask import session, redirect, url_for, request, flash

from WebUI.config import ADMIN_USERNAME, ADMIN_PASSWORD


def login_required(view):
    """
    用于装饰需要登录才能访问的视图函数
    
    参数:
        view: 视图函数
    
    返回:
        装饰后的视图函数
    """

    @functools.wraps(view)
    def wrapped_view(**kwargs):
        # 检查会话中是否有 authenticated 标志
        if not session.get('authenticated', False):
            # 保存请求的URL用于登录后重定向
            session['redirect_url'] = request.url
            flash('请先登录后访问此页面', 'warning')
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view


def verify_credentials(username, password):
    """
    验证用户名和密码
    
    参数:
        username: 用户名
        password: 密码
    
    返回:
        bool: 验证是否成功
    """
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD
