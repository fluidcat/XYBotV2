import asyncio
import os
import pathlib

import xywechatpad_binary
from loguru import logger


class WechatAPIServer:
    def __init__(self):
        self.executable_path = xywechatpad_binary.copy_binary(pathlib.Path(__file__).parent.parent / "core")
        self.executable_path = self.executable_path.absolute()

        self.server_task = None
        self.log_task = None
        self.process = None

    async def start(self, port=9000, mode="release", redis_host="127.0.0.1",
                    redis_port=6379, redis_password="", redis_db=0):
        """异步启动服务"""
        command = [
            self.executable_path,
            "-p", str(port),
            "-m", mode,
            "-rh", redis_host,
            "-rp", str(redis_port),
            "-rpwd", redis_password,
            "-rdb", str(redis_db)
        ]

        # 使用异步创建子进程
        self.process = await asyncio.create_subprocess_exec(
            *command,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # 启动日志监控任务
        self.log_task = asyncio.create_task(self.process_log())

    async def stop(self):
        """异步停止服务"""
        if hasattr(self, 'process'):
            try:
                if not self.log_task.done():
                    self.log_task.cancel()
                await asyncio.gather(self.log_task, return_exceptions=True)
                self.log_task = None

                self.process.terminate()
                await self.process.wait()
            except ProcessLookupError:
                logger.warning("尝试终止已退出的进程")

    async def process_log(self):
        """处理子进程的日志输出"""
        try:
            # 创建两个独立的任务来分别处理stdout和stderr
            stdout_task = asyncio.create_task(self._read_stream(self.process.stdout, "info"))
            stderr_task = asyncio.create_task(self._read_stream(self.process.stderr, "error"))

            # 等待两个任务中的任何一个完成
            codes = await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
            logger.info(f"WechatAPI已退出，返回码: {codes[0]}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"处理日志时发生错误: {e}")

    async def _read_stream(self, stream, log_level):
        """读取流并记录日志"""
        while True:
            line = await stream.readline()
            if not line:  # EOF
                if self.process.returncode is not None:
                    return self.process.returncode
                await asyncio.sleep(0.1)
                continue

            text = line.decode('utf-8', errors='replace').strip()
            if text:
                if log_level == "info":
                    logger.log("API", text)
                else:
                    logger.log("API", text)
        return self.process.returncode


wechat_api_server = WechatAPIServer()
