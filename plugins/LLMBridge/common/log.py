import os
import logging

from loguru import logger as loguru_logger
import sys


class PropagateHandler(logging.Handler):
    def emit(self, record):
        # 将 logging 的日志记录传递给 loguru
        logger_opt = loguru_logger.opt(depth=6, exception=record.exc_info)
        logger_opt.log(record.levelname, record.getMessage())


def _reset_logger(log):
    for handler in log.handlers:
        handler.close()
        log.removeHandler(handler)
        del handler
    log.handlers.clear()
    log.propagate = False
    log.addHandler(PropagateHandler())


def _get_logger():
    log = logging.getLogger("log")
    _reset_logger(log)
    log.setLevel(logging.DEBUG)
    return log


# 日志句柄
logger = _get_logger()
