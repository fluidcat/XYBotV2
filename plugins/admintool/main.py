import os  # 确保导入os模块

import requests
from loguru import logger

from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.plugin_base import PluginBase


class AdminTool(PluginBase):
    description = "停止服务插件"
    author = "fluidcat"
    version = "1.0.0"

    # 同步初始化
    def __init__(self):
        super().__init__()

        # 获取配置文件路径
        config_path = os.path.join(os.path.dirname(__file__), "config.toml")
        config = self.loadConfig(config_path).get("admintool", {})
        # 读取基本配置
        self.enable = config.get("enable", False)  # 读取插件开关
        self.enable_schedule = config.get("enable_schedule", False)  # 读取插件开关

        sys_config = self.loadConfig("main_config.toml").get('XYBot')

    # 异步初始化
    async def async_init(self):
        return

    @on_text_message(priority=55)
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        cmd = message.get("command", "")
        if not cmd.startswith("#") or cmd != '#停止响应':
            return
        bot.stop_sync_message = True
        logger.info("xybot 已经停止处理消息")
        await bot.send_reply_message(message, "我已经停止处理消息")
        return False

    @on_at_message(priority=50)
    async def handle_at(self, bot: WechatAPIClient, message: dict):
        return await self.handle_text(bot, message)

    @schedule('interval', minutes=30)
    async def log_monitor(self, bot: WechatAPIClient):
        """
            定期监控日志文件，检查是否存在特定关键词
            """
        log_file_path = "logs/xybot.log"
        keywords = ["用户可能退出", "数据[DecryptData]失败"]
        max_lines_to_read = 10  # 最多读取的行数

        if not os.path.exists(log_file_path):
            logger.warning(f"日志文件不存在: {log_file_path}")
            return

        try:
            # 从文件末尾逐行读取日志
            found_keywords = set()  # 使用集合避免重复关键词
            with open(log_file_path, "rb") as log_file:
                # 定位到文件末尾
                log_file.seek(0, os.SEEK_END)
                file_size = log_file.tell()
                buffer_size = 1024  # 每次读取的缓冲区大小
                data = b""
                lines_read = 0

                # 从后向前读取文件内容
                while file_size > 0 and lines_read < max_lines_to_read:
                    # 计算本次读取的位置
                    read_size = min(buffer_size, file_size)
                    file_size -= read_size
                    log_file.seek(file_size, os.SEEK_SET)
                    data = log_file.read(read_size) + data

                    # 按行分割数据
                    lines = data.splitlines()
                    if len(lines) > 1:
                        # 保留未完整读取的行
                        data = lines[0]
                        lines = lines[1:]
                    else:
                        continue

                    # 检查每一行是否包含关键词
                    for line in reversed(lines):
                        try:
                            line = line.decode("utf-8")  # 解码为字符串
                            for keyword in keywords:
                                if keyword in line:
                                    found_keywords.add(keyword)
                            lines_read += 1
                            if lines_read >= max_lines_to_read:
                                break
                        except UnicodeDecodeError:
                            logger.warning("日志文件包含无法解码的内容")

            # 如果找到关键词，记录日志并发送通知
            if found_keywords:
                logger.warning(f"在日志中发现关键词: {', '.join(found_keywords)}")
                self.send_pushplus_message('wxbot接收消息异常', ', '.join(found_keywords))

        except Exception as e:
            logger.error(f"读取日志文件时发生错误: {e}")

    def send_pushplus_message(self, title: str, content: str) -> bool:
        """
        使用 PushPlus API 发送消息

        :param token: PushPlus 的 token
        :param title: 消息标题
        :param content: 消息内容
        :param topic: 消息主题，默认为 "test"
        :return: 是否发送成功
        """
        url = "http://www.pushplus.plus/send/"
        payload = {
            "token": os.getenv("XYBOT_ADMINTOOL__PUSHPLUS_TOKEN"),
            "title": title,
            "content": content,
        }

        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()  # 检查请求是否成功
            logger.info(f"PushPlus 消息发送成功: {response.json()}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"PushPlus 消息发送失败: {e}")
            return False
