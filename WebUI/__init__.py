import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any, Union

# 添加 monkey patch 修复 Flask-Session 与 Werkzeug 的兼容性问题
import flask_session.sessions
from flask import Flask, redirect, url_for
from flask_login import LoginManager
from flask_session import Session
from flask_socketio import SocketIO
from loguru import logger

# 保存原始的 save_session 方法
original_save_session = flask_session.sessions.FileSystemSessionInterface.save_session

# 创建修复的 save_session 方法
def patched_save_session(self, app, session, response):
    # 如果会话 ID 是字节类型，转换为字符串
    if hasattr(self, 'get_session_id') and callable(self.get_session_id):
        original_get_session_id = self.get_session_id
        
        def wrapped_get_session_id(session):
            session_id = original_get_session_id(session)
            if isinstance(session_id, bytes):
                return session_id.decode('utf-8')
            return session_id
            
        self.get_session_id = wrapped_get_session_id
    
    # 调用原始方法
    return original_save_session(self, app, session, response)

# 应用 monkey patch
flask_session.sessions.FileSystemSessionInterface.save_session = patched_save_session


class InterceptHandler(logging.Handler):
    """将标准日志重定向到loguru的处理器
    
    此类拦截标准logging模块的日志记录，并将其重定向到loguru，
    确保所有日志使用统一的格式和处理方式。
    """

    def emit(self, record: logging.LogRecord) -> None:
        """处理日志记录并转发到loguru
        
        Args:
            record: 标准日志模块的日志记录对象
        """
        logger_opt = logger.opt(depth=6, exception=record.exc_info)
        logger_opt.log('WEBUI', record.getMessage())


def _configure_logging(app: Flask) -> None:
    """配置应用日志系统，使用loguru处理所有日志
    
    Args:
        app: Flask应用实例
    """
    # 清除Flask默认日志处理器并配置使用loguru
    app.logger.handlers = []
    app.logger.propagate = False
    app.logger.addHandler(InterceptHandler())

    # 同样为werkzeug日志配置loguru
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.handlers = []
    werkzeug_logger.propagate = False
    werkzeug_logger.addHandler(InterceptHandler())

    logger.log('WEBUI', "日志系统已配置为使用loguru")


def _setup_instance_directories(app: Flask) -> None:
    """确保应用所需的实例目录存在
    
    Args:
        app: Flask应用实例
    """
    try:
        os.makedirs(app.instance_path, exist_ok=True)
        os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
        logger.log('WEBUI', f"已创建实例目录: {app.instance_path}")
    except OSError as e:
        logger.log('WEBUI', f"创建实例目录失败: {e}")


def create_app(test_config: Optional[Dict[str, Any]] = None) -> Tuple[Flask, SocketIO]:
    """创建并配置Flask应用实例及SocketIO实例
    
    Args:
        test_config: 可选的测试配置字典，用于测试环境
        
    Returns:
        tuple: 包含配置好的Flask应用实例和SocketIO实例
    """
    # 创建Flask应用，设置静态文件和模板路径
    app = Flask(__name__,
                instance_relative_config=True,
                static_folder='static',
                template_folder='templates')

    logger.log('WEBUI', "正在初始化XYBotV2 WebUI应用...")

    # 加载默认配置
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_key_please_change_in_production'),
        SESSION_TYPE='filesystem',
        SESSION_FILE_DIR=os.path.join(app.instance_path, 'flask_session'),
        SESSION_PERMANENT=True,
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
        SESSION_USE_SIGNER=True,
    )

    # 加载实例配置（如果存在）
    if test_config is None:
        # 非测试模式下，从配置文件加载
        app.config.from_pyfile('config.py', silent=True)
        logger.log('WEBUI', "已从config.py加载配置")
    else:
        # 测试模式下，使用传入的配置
        app.config.from_mapping(test_config)
        logger.log('WEBUI', "已加载测试配置")

    # 确保实例文件夹存在
    _setup_instance_directories(app)

    # 配置日志系统
    _configure_logging(app)

    # 初始化Flask-Session
    Session(app)
    logger.log('WEBUI', "已初始化会话管理")

    # 初始化Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    logger.log('WEBUI', "已初始化用户认证系统")

    # 注册模板过滤器
    from .utils.template_filters import register_template_filters
    register_template_filters(app)
    logger.log('WEBUI', "已注册模板过滤器")

    # 注册蓝图
    from .routes import register_blueprints
    register_blueprints(app)
    logger.log('WEBUI', "已注册路由蓝图")

    # 初始化WebSocket服务
    from .services.websocket_service import socketio, init_websocket

    # 配置socketio
    socketio_config = {
        'cors_allowed_origins': '*',  # 允许的跨域来源，生产环境应该更严格
        'async_mode': 'eventlet',  # 使用eventlet作为异步模式
        'logger': False,  # 禁用socketio日志
        'engineio_logger': False  # 禁用engineio日志
    }

    # 初始化socketio
    socketio.init_app(app, **socketio_config)
    logger.log('WEBUI', "已初始化SocketIO服务")

    # 启动WebSocket服务
    init_websocket()
    logger.log('WEBUI', "已启动WebSocket日志监控")

    # 注册全局上下文处理器
    @app.context_processor
    def inject_global_vars() -> Dict[str, Union[str, datetime]]:
        """为所有模板注入全局变量
        
        Returns:
            包含全局变量的字典
        """
        return {
            'app_name': 'XYBotV2 WebUI',
            'version': '1.0.0',
            'now': datetime.now()
        }

    # 定义用户加载函数
    @login_manager.user_loader
    def load_user(user_id: str) -> Any:
        """根据用户ID加载用户对象
        
        Args:
            user_id: 用户的唯一标识符
            
        Returns:
            用户对象或None（如果用户不存在）
        """
        from .models import User
        return User.get(user_id)

    # 简单的首页路由（重定向到概览页）
    @app.route('/')
    def index():
        """应用首页路由处理，重定向到概览页"""
        return redirect(url_for('overview.index'))

    logger.log('WEBUI', "XYBotV2 WebUI应用初始化完成")
    return app, socketio
