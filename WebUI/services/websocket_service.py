import threading
import time
from pathlib import Path

from flask_socketio import SocketIO, emit
from loguru import logger

from WebUI.services.data_service import BOT_LOG_PATH

# 创建SocketIO实例 - 但不在这里初始化，而是通过工厂函数传入
socketio = SocketIO()


class LogWatcher:
    """日志监控器，用于实时推送新的日志"""

    def __init__(self, socketio_instance):
        """初始化日志监控器
        
        Args:
            socketio_instance: SocketIO实例，用于推送WebSocket消息
        """
        self.socketio = socketio_instance
        self.running = False
        self.watch_thread = None
        self.last_position = 0
        self.last_emit_time = 0
        self.buffer = []
        self.throttle_interval = 1.0  # 限制发送频率为1秒
        self.thd = TimerThread(self._handle_log)

    def start(self):
        """启动日志监控线程"""
        if self.running:
            return

        self.running = True
        logger.add(self._handle_log, enqueue=True)
        self.thd.start()
        logger.info("日志WebSocket监控已启动")

    def stop(self):
        """停止日志监控线程"""
        self.running = False
        if self.watch_thread and self.watch_thread.is_alive():
            self.watch_thread.join(timeout=1.0)
        if self.thd and self.thd.is_alive():
            self.thd.stop()
            self.thd.join(timeout=1.0)
        logger.info("WebSocket日志监控服务已关闭")

    def _should_ignore_log(self, log_line):
        """判断是否应该忽略某条日志
        
        Args:
            log_line: 日志行文本
            
        Returns:
            bool: 如果应该忽略则返回True
        """
        # 忽略WebSocket自身的调试日志，避免循环
        if "WebUI.services.websocket_service" in log_line and "已推送" in log_line:
            return True

        # 忽略SocketIO的emitting日志
        if log_line.startswith("emitting event"):
            return True

        # 忽略空日志
        if not log_line.strip():
            return True

        return False

    def _emit_logs(self):
        """发送缓冲区中的日志"""

        _buffer = self.buffer
        # 无论是否发送，都清空缓冲区
        self.buffer = []

        if not _buffer:
            return

        # 过滤掉应该忽略的日志
        filtered_logs = [log for log in _buffer if not self._should_ignore_log(log)]

        # 如果过滤后还有日志需要发送
        if filtered_logs:
            self.socketio.emit('new_logs', {'logs': filtered_logs})

        self.last_emit_time = time.time()

    def _handle_log(self, log_data=None):
        """监控日志文件变化并推送新日志到WebSocket连接"""
        if self.running:
            try:
                new_logs = [str(log_data)] if log_data else None
                if new_logs:
                    # 添加到缓冲区
                    self.buffer.extend(new_logs)
                    # 检查是否应该发送
                    current_time = time.time()
                    if current_time - self.last_emit_time >= self.throttle_interval:
                        self._emit_logs()
                # 如果缓冲区有内容且超过了节流时间，发送日志
                elif self.buffer and time.time() - self.last_emit_time >= self.throttle_interval:
                    self._emit_logs()

            except Exception as e:
                logger.error(f"监控日志文件出错: {str(e)}")

    def get_historical_logs(self, n=100):
        """获取历史日志
        
        Args:
            n: 要获取的日志行数，默认100行
            
        Returns:
            list: 日志行列表
        """
        try:
            if isinstance(BOT_LOG_PATH, str):
                log_path = Path(BOT_LOG_PATH)
            else:
                log_path = BOT_LOG_PATH

            if not log_path.exists():
                return []

            # 使用tail命令的逻辑，从文件末尾读取n行
            with open(log_path, 'r', encoding='utf-8') as f:
                # 先获取所有行
                all_lines = f.readlines()

            # 获取最后n行
            last_n_lines = all_lines[-n:] if len(all_lines) > n else all_lines

            # 过滤并处理日志行
            logs = [line.strip() for line in last_n_lines if line.strip()]
            filtered_logs = [log for log in logs if not self._should_ignore_log(log)]

            return filtered_logs
        except Exception as e:
            logger.error(f"获取历史日志出错: {str(e)}")
            return []


# 全局变量，保存LogWatcher实例
log_watcher = None


def init_websocket():
    """初始化WebSocket服务，启动日志监控器"""
    global log_watcher

    # 确保只初始化一次
    if log_watcher is None:
        log_watcher = LogWatcher(socketio)
        log_watcher.start()

        # 注册事件处理函数
        @socketio.on('request_logs')
        def handle_request_logs(data):
            """处理客户端请求日志事件
            
            Args:
                data: 客户端发送的数据，包含n表示请求的日志行数
            """
            try:
                # 获取客户端请求的日志行数，默认100行
                n = data.get('n', 100) if isinstance(data, dict) else 100
                # 获取历史日志
                logs = log_watcher.get_historical_logs(n)
                # 发送给请求的客户端
                emit('new_logs', {'logs': logs})
            except Exception as e:
                logger.error(f"处理日志请求出错: {str(e)}")
    else:
        logger.debug("WebSocket日志监控服务已初始化")


def shutdown_websocket():
    """关闭WebSocket服务，停止日志监控器"""
    global log_watcher

    if log_watcher is not None:
        log_watcher.stop()
        log_watcher = None
        logger.info("WebSocket日志监控服务已关闭")


class TimerThread(threading.Thread):
    def __init__(self, func, interval: float = 1.0):
        super().__init__()
        self.stop_event = threading.Event()
        self.func = func
        self.interval = interval
        self.name = 'log-watch-thread'

    def run(self):
        while not self.stop_event.is_set():
            self.func()
            self.stop_event.wait(self.interval)

    def stop(self):
        self.stop_event.set()
