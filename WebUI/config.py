import os
import tomllib
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 尝试读取主配置文件
try:
    with open(BASE_DIR / 'main_config.toml', 'rb') as f:
        toml_config = tomllib.load(f)
        WEBUI_CONFIG = toml_config.get('WebUI', {})
except (FileNotFoundError, tomllib.TOMLDecodeError):
    WEBUI_CONFIG = {}

# Flask应用配置
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_key_please_change_in_production')
# DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
DEBUG = True

# 会话配置
SESSION_TYPE = 'filesystem'
SESSION_PERMANENT = True
PERMANENT_SESSION_LIFETIME = int(WEBUI_CONFIG.get('session-timeout', 30)) * 60  # 转换为秒

# 认证相关配置
ADMIN_USERNAME = WEBUI_CONFIG.get('admin-username', 'admin')
ADMIN_PASSWORD = WEBUI_CONFIG.get('admin-password', 'admin123')

# 日志配置
LOG_LEVEL = 'DEBUG' if DEBUG else 'INFO'
LOG_FILE = BASE_DIR / 'logs' / 'webui.log'
