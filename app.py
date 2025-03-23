import asyncio
import os
import signal
import sys

from loguru import logger

# 在任何导入之前设置日志级别
logger.remove()
logger.level("WEBUI", no=20, color="<blue>")
logger.level("API", no=1, color="<blue>")
logger.add(sys.stdout, level="INFO", colorize=True,
           format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}")
logger.add("logs/xybot.log", rotation="10mb", level="DEBUG", encoding="utf-8")
logger.add("logs/wechatapi.log", level="DEBUG", filter=lambda r: r["level"].name == "API")
logger.add("logs/webui.log", level="WEBUI", filter=lambda r: r["level"].name == "WEBUI")

# 导入eventlet并应用猴子补丁
import eventlet

eventlet.monkey_patch()

# 现在可以安全地导入其他模块
from WebUI import create_app
from WebUI.services.websocket_service import shutdown_websocket
from database.XYBotDB import XYBotDB
from database.keyvalDB import KeyvalDB
from database.messsagDB import MessageDB

# 全局变量
message_db = None
keyval_db = None
_is_shutting_down = False


async def init_system():
    """初始化系统数据库连接"""
    global message_db, keyval_db
    try:
        logger.info("正在初始化数据库连接...")
        XYBotDB()
        message_db = MessageDB()
        await message_db.initialize()
        keyval_db = KeyvalDB()
        await keyval_db.initialize()
        await keyval_db.delete("start_time")
        logger.success("数据库初始化成功")
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        raise


async def shutdown_system():
    """关闭系统连接和资源"""
    global _is_shutting_down, message_db, keyval_db
    if _is_shutting_down:
        return
    _is_shutting_down = True

    logger.info("正在关闭系统资源...")

    # 关闭WebSocket服务
    try:
        shutdown_websocket()
    except Exception as e:
        logger.error(f"关闭WebSocket服务时出错: {str(e)}")

    # 关闭数据库连接
    logger.info("正在关闭数据库连接...")
    for db, name in [(message_db, "消息数据库"), (keyval_db, "键值数据库")]:
        if db:
            try:
                await db.close()
                logger.info(f"{name}连接已关闭")
            except Exception as e:
                logger.error(f"关闭{name}连接时出错: {str(e)}")

    message_db = keyval_db = None
    logger.success("所有系统资源已关闭")


def run_async_safely(coro):
    """安全运行异步协程，处理事件循环问题
    
    Args:
        coro: 要运行的异步协程
    """
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
    """处理终止信号
    
    Args:
        signum: 信号编号
        _: 信号帧（未使用）
    """
    logger.info(f"收到 {signum} 信号, 退出中...")
    run_async_safely(shutdown_system())
    sys.exit(0)


# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def main():
    """应用主入口函数"""
    try:
        # 初始化系统
        asyncio.run(init_system())

        # 创建Flask应用和socketio
        app, socketio = create_app()

        # 运行Web服务器
        host = os.environ.get('FLASK_HOST', '0.0.0.0')
        port = int(os.environ.get('FLASK_PORT', 9999))
        debug = False  # 禁用debug模式以防止双重初始化

        logger.info(f"WebUI服务启动于 http://{host}:{port}/")
        socketio.run(app, host=host, port=port, debug=debug)

    except KeyboardInterrupt:
        logger.info("接收到中断信号，开始优雅关闭...")
    except Exception as e:
        logger.error(f"应用运行时发生错误: {str(e)}")
    finally:
        run_async_safely(shutdown_system())


if __name__ == '__main__':
    main()
