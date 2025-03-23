import asyncio
import os
import signal
import sys

from loguru import logger

from WebUI import create_app
from database.XYBotDB import XYBotDB
from database.keyvalDB import KeyvalDB
from database.messsagDB import MessageDB

# Global variables
message_db = None
keyval_db = None
_is_shutting_down = False

# Check if we're in the Flask reloader process
is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'

# Setup logging
logger.remove()
logger.level("WEBUI", no=20, color="<blue>")
logger.add(sys.stdout, level="INFO", colorize=True,
           format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}")
logger.add("logs/xybot.log", rotation="10mb", level="DEBUG", encoding="utf-8")
logger.add("logs/wechatapi.log", level="DEBUG", filter=lambda r: r["level"].name == "API")
logger.add("logs/webui.log", level="WEBUI", filter=lambda r: r["level"].name == "WEBUI")


async def init_system():
    """Initialize database connections"""
    global message_db, keyval_db
    XYBotDB()
    message_db = MessageDB()
    await message_db.initialize()
    keyval_db = KeyvalDB()
    await keyval_db.initialize()
    await keyval_db.delete("start_time")
    logger.success("数据库初始化成功")


async def shutdown_system():
    """Close database connections"""
    global _is_shutting_down, message_db, keyval_db
    if _is_shutting_down:
        return
    _is_shutting_down = True

    logger.info("正在关闭数据库连接...")
    for db, name in [(message_db, "消息数据库"), (keyval_db, "键值数据库")]:
        if db:
            try:
                await db.close()
                logger.info(f"{name}连接已关闭")
            except Exception as e:
                logger.error(f"关闭{name}连接时出错: {str(e)}")

    message_db = keyval_db = None
    logger.success("所有数据库连接已关闭")


def run_async_safely(coro):
    """Run an async coroutine safely, handling event loop issues"""
    try:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, loop).result(timeout=5)
        else:
            loop.run_until_complete(coro)
    except Exception as e:
        logger.error(f"异步任务执行失败: {str(e)}")


def signal_handler(signum, _):
    """Handle termination signals"""
    logger.info(f"收到 {signum} 信号, 退出中...")
    run_async_safely(shutdown_system())
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Create Flask app
app, socketio = create_app()

if __name__ == '__main__':
    # Initialize system - only in reloader process or if debug mode is disabled
    # This prevents double initialization when Flask auto-reloads in debug mode
    asyncio.run(init_system())

    # Run web server
    try:
        host = os.environ.get('FLASK_HOST', '0.0.0.0')
        port = int(os.environ.get('FLASK_PORT', 9999))
        # Always disable debug mode to prevent double initialization
        debug = False
        socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        logger.info("接收到中断信号，开始优雅关闭...")
    except Exception as e:
        logger.error(f"应用运行时发生错误: {str(e)}")
    finally:
        run_async_safely(shutdown_system())
