import asyncio
import os
import sys
import time
import tomllib
import traceback
from pathlib import Path

from loguru import logger
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from bot_core import bot_core


def is_api_message(record):
    return record["level"].name == "API"


class ConfigChangeHandler(FileSystemEventHandler):
    def __init__(self, restart_callback):
        self.restart_callback = restart_callback
        self.last_triggered = 0
        self.cooldown = 2  # 冷却时间(秒)
        self.waiting_for_change = False  # 是否在等待文件改变

    def on_modified(self, event):
        if not event.is_directory:
            current_time = time.time()
            if current_time - self.last_triggered < self.cooldown:
                return

            file_path = Path(event.src_path).resolve()
            if (file_path.name == "main_config.toml" or
                    "plugins" in str(file_path) and file_path.suffix in ['.py', '.toml']):
                logger.info(f"检测到文件变化: {file_path}")
                self.last_triggered = current_time
                if self.waiting_for_change:
                    logger.info("检测到文件改变，正在重启...")
                    self.waiting_for_change = False
                self.restart_callback()


async def main():
    # 设置工作目录为脚本所在目录
    script_dir = Path(__file__).resolve().parent
    os.chdir(script_dir)
    
    # 读取配置文件
    config_path = script_dir / "main_config.toml"
    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    # 检查是否启用自动重启
    auto_restart = config.get("XYBot", {}).get("auto-restart", False)

    if auto_restart:
        # 设置监控
        observer = Observer()
        script_dir = Path(__file__).parent
        config_path = script_dir / "main_config.toml"
        plugins_path = script_dir / "plugins"

        handler = ConfigChangeHandler(None)

        def restart_program():
            logger.info("正在重启程序...")
            # 清理资源
            observer.stop()
            try:
                import multiprocessing.resource_tracker
                multiprocessing.resource_tracker._resource_tracker.clear()
            except Exception as e:
                logger.warning(f"清理资源时出错: {e}")
            # 重启程序
            os.execv(sys.executable, [sys.executable] + sys.argv)

        handler.restart_callback = restart_program
        observer.schedule(handler, str(config_path.parent), recursive=False)
        observer.schedule(handler, str(plugins_path), recursive=True)
        observer.start()

        try:
            await bot_core()
        except KeyboardInterrupt:
            logger.info("收到终止信号，正在关闭...")
            observer.stop()
            observer.join()
        except Exception as e:
            logger.error(f"程序发生错误: {e}")
            logger.error(traceback.format_exc())
            logger.info("等待文件改变后自动重启...")
            handler.waiting_for_change = True

            while handler.waiting_for_change:
                await asyncio.sleep(1)
    else:
        # 直接运行主程序，不启用监控
        try:
            await bot_core()
        except KeyboardInterrupt:
            logger.info("收到终止信号，正在关闭...")
        except Exception as e:
            logger.error(f"发生错误: {e}")
            logger.error(traceback.format_exc())


if __name__ == "__main__":
    # 防止低版本Python运行
    if sys.version_info.major != 3 and sys.version_info.minor != 11:
        print("请使用Python3.11")
        sys.exit(1)
    print(
        "░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓███████▓▒░ ░▒▓██████▓▒░▒▓████████▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓███████▓▒░  \n"
        "░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ ░▒▓█▓▒░          ░▒▓█▓▒░░▒▓█▓▒░      ░▒▓█▓▒░ \n"
        "░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ ░▒▓█▓▒░           ░▒▓█▓▒▒▓█▓▒░       ░▒▓█▓▒░ \n"
        " ░▒▓██████▓▒░ ░▒▓██████▓▒░░▒▓███████▓▒░░▒▓█▓▒░░▒▓█▓▒░ ░▒▓█▓▒░           ░▒▓█▓▒▒▓█▓▒░ ░▒▓██████▓▒░  \n"
        "░▒▓█▓▒░░▒▓█▓▒░  ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ ░▒▓█▓▒░            ░▒▓█▓▓█▓▒░ ░▒▓█▓▒░        \n"
        "░▒▓█▓▒░░▒▓█▓▒░  ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ ░▒▓█▓▒░            ░▒▓█▓▓█▓▒░ ░▒▓█▓▒░        \n"
        "░▒▓█▓▒░░▒▓█▓▒░  ░▒▓█▓▒░   ░▒▓███████▓▒░ ░▒▓██████▓▒░  ░▒▓█▓▒░             ░▒▓██▓▒░  ░▒▓████████▓▒░\n")

    logger.remove()

    logger.level("API", no=1, color="<cyan>")

    logger.add(
        "logs/XYBot_{time:YYYY_MM_DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        encoding="utf-8",
        enqueue=True,
        retention="2 weeks",
        rotation=lambda message, file: os.path.getsize(file.name) > 100 * 1024 * 1024,
        backtrace=True,
        diagnose=True,
        level="INFO",
    )
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}",
        level="TRACE",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    asyncio.run(main())
