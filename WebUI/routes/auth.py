from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, session, flash, current_app

from WebUI.config import PERMANENT_SESSION_LIFETIME
from WebUI.forms.auth_forms import LoginForm
from WebUI.utils.auth_utils import verify_credentials, login_required

# 创建认证蓝图
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    # 已登录用户直接跳转到首页
    if session.get('authenticated'):
        return redirect(url_for('overview.index'))

    form = LoginForm()

    # 表单提交处理
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        if verify_credentials(username, password):
            # 设置会话信息
            session['authenticated'] = True
            session['username'] = username
            session['login_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 设置会话超时时间
            session.permanent = True

            # 如果用户勾选"记住我"，延长会话时间
            if form.remember_me.data:
                # 延长会话时间为配置的两倍
                current_app.permanent_session_lifetime = timedelta(seconds=PERMANENT_SESSION_LIFETIME * 2)

            # 获取请求来源并重定向
            next_url = session.pop('redirect_url', None)
            if next_url:
                return redirect(next_url)
            return redirect(url_for('overview.index'))
        else:
            flash('用户名或密码错误', 'danger')

    # GET请求渲染登录页面
    return render_template('auth/login.html', form=form, now=datetime.now())


@auth_bp.route('/logout')
@login_required
def logout():
    """用户登出"""
    # 清除会话信息
    session.clear()
    flash('您已成功退出登录', 'success')
    return redirect(url_for('auth.login'))
