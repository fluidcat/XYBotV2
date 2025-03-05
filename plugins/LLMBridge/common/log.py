import os

from loguru import logger as logging
import sys


def _reset_logger(log):
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


def _get_logger():
    return logging


# 日志句柄
logger = _get_logger()
