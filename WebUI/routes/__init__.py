def register_blueprints(app):
    """
    注册所有蓝图到Flask应用
    
    参数:
        app: Flask应用实例
    """
    # 导入所有蓝图
    from .auth import auth_bp
    from .overview import overview_bp
    from .logs import logs_bp
    from .config import config_bp
    from .plugin import plugin_bp
    from .tools import tools_bp
    from .file import file_bp
    from .bot import bot_bp
    from .explorer import explorer_bp
    from .about import about_bp

    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(overview_bp)
    app.register_blueprint(logs_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(plugin_bp)
    app.register_blueprint(tools_bp)
    app.register_blueprint(file_bp)
    app.register_blueprint(bot_bp)
    app.register_blueprint(explorer_bp)
    app.register_blueprint(about_bp)
