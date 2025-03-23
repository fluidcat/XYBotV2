from datetime import datetime


def timestamp_to_datetime(timestamp):
    """
    将时间戳转换为格式化日期时间字符串
    
    参数:
        timestamp (float): UNIX时间戳
        
    返回:
        str: 格式化的日期时间字符串
    """
    if not timestamp:
        return "未知"

    try:
        dt = datetime.fromtimestamp(float(timestamp))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return "无效时间戳"


def format_file_size(size_bytes):
    """
    格式化文件大小
    
    参数:
        size_bytes (int): 文件大小（字节）
        
    返回:
        str: 格式化的文件大小字符串
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def register_template_filters(app):
    """
    注册所有模板过滤器到Flask应用
    
    参数:
        app: Flask应用实例
    """
    app.jinja_env.filters['timestamp_to_datetime'] = timestamp_to_datetime
    app.jinja_env.filters['format_file_size'] = format_file_size
