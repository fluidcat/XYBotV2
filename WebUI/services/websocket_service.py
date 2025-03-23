import os
import threading
import time

from flask import request
from flask_socketio import SocketIO
from loguru import logger

from WebUI.services.data_service import data_service, BOT_LOG_PATH

# 创建SocketIO实例
socketio = SocketIO()


class LogWatcher:
    """日志监控器，用于实时推送新的日志"""

    def __init__(self, socketio_instance):
        self.socketio = socketio_instance
        self.running = False
        self.watch_thread = None
        self.last_position = 0
        self._init_watcher()

    def _init_watcher(self):
        """初始化日志监控器"""
        # 获取当前日志文件大小作为起始位置
        if BOT_LOG_PATH.exists():
            self.last_position = os.path.getsize(BOT_LOG_PATH)
        else:
            self.last_position = 0

    def start(self):
        """启动日志监控"""
        if self.running:
            return

        self.running = True
        self.watch_thread = threading.Thread(target=self._watch_log_file, daemon=True)
        self.watch_thread.start()
        logger.info("日志WebSocket监控已启动")

    def stop(self):
        """停止日志监控"""
        self.running = False
        if self.watch_thread and self.watch_thread.is_alive():
            self.watch_thread.join(timeout=1.0)
        logger.info("日志WebSocket监控已停止")

    def _watch_log_file(self):
        """监控日志文件变化并推送新日志"""
        while self.running:
            try:
                if not BOT_LOG_PATH.exists():
                    time.sleep(1)
                    continue

                current_size = os.path.getsize(BOT_LOG_PATH)

                # 如果文件大小变小，说明日志被轮转或清空，重置位置
                if current_size < self.last_position:
                    self.last_position = 0

                # 有新日志
                if current_size > self.last_position:
                    with open(BOT_LOG_PATH, 'r', encoding='utf-8') as f:
                        # 移动到上次读取的位置
                        f.seek(self.last_position)
                        # 读取新增内容
                        new_lines = f.readlines()
                        new_logs = [line.strip() for line in new_lines]

                        if new_logs:
                            # 推送新日志到所有连接的客户端
                            self.socketio.emit('new_logs', {'logs': new_logs})

                    # 更新位置指针
                    self.last_position = current_size

            except Exception as e:
                logger.error(f"监控日志文件出错: {str(e)}")

            # 短暂休眠，避免过高CPU占用
            time.sleep(0.5)


# 创建日志监控实例
log_watcher = None


def init_websocket(app):
    """初始化WebSocket服务"""
    global log_watcher
    socketio.init_app(app, cors_allowed_origins="*", async_mode="threading")

    @socketio.on('connect')
    def handle_connect():
        """处理客户端连接事件"""
        client_id = request.sid

        # 连接后立即发送一些初始日志，提高用户体验
        try:
            logs = data_service.get_recent_logs(50)
            if not logs:
                logs = ["暂无日志记录"]

            socketio.emit('logs_response', {'logs': logs}, room=client_id)
        except Exception as e:
            logger.error(f"发送初始日志时出错: {str(e)}")

    @socketio.on('disconnect')
    def handle_disconnect():
        pass

    @socketio.on('request_logs')
    def handle_request_logs(data):
        """处理请求历史日志的事件"""
        n = data.get('n', 100)
        logs = data_service.get_recent_logs(n)

        # 确保logs不为空，如果为空则发送一个默认消息
        if not logs:
            logs = ["暂无日志记录"]

        # 直接发送到请求的客户端
        socketio.emit('logs_response', {'logs': logs}, room=request.sid)

    # 启动日志监控
    log_watcher = LogWatcher(socketio)
    log_watcher.start()

    return socketio
