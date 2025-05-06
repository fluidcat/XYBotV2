import json
import mimetypes
import os  # 确保导入os模块
import textwrap
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

import aiohttp
import filetype
from apscheduler.triggers.date import DateTrigger

from WechatAPI import WechatAPIClient
from database.user_schedule_task import UserScheduleTask, UserScheduleTaskDB
from plugins.LLMBridge.bot.bot_factory import create_bot
from plugins.LLMBridge.bridge.context import Context, ContextType
from plugins.LLMBridge.common import const
from plugins.LLMBridge.role import RolePlay
from utils.const import *
from utils.decorators import *
from utils.plugin_base import PluginBase


class RemindPlugin(PluginBase):
    description = "提醒插件"
    author = "fluidcat"
    version = "1.0.0"

    # 同步初始化
    def __init__(self):
        super().__init__()

        # 获取配置文件路径
        self.timezone = ZoneInfo('Asia/Shanghai')
        self.wx_bot: Optional[WechatAPIClient] = None
        config_path = os.path.join(os.path.dirname(__file__), "config.toml")
        config = self.loadConfig(config_path).get("RemindPlugin", {})

        # 读取基本配置
        self.enable = config.get("enable", False)  # 读取插件开关

        self.ai_bot = create_bot(const.ZHIPU_AI)
        self.model = 'glm-4-flash'
        self.prompt = (
                "你是智能定时任务生成助手，根据用户提供的任务描述、时间要求，自动生成一个可执行的定时任务方案，现在时间是："
                + f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}。'
                + textwrap.dedent("""
                        1、如果用户输入内容不是定时任务，则定时任务为空：{}
                        2、如果用户输入内容是定时的任务相关，则要求生成定时任务：
                        - 判断是重复任务还是一次性任务
                        - 定时任务格式：
                            task(任务描述)：xxxx（一句话描述）
                            msg(提醒语)：友好的提醒文字（要友好！！！重要！！！）
                            task_type(任务类型)：一次性任务或重复任务
                            tip(添加成功提示)：xxxxxx
                            task_scope:(任务有效时长,month-任务有效期是整个月,day-任务有效期是一整天,hour-任务有效期是一个小时,time-任务只在某个时间点有效,other-其他)：任务的有效时长，重点你要判断是时长还是时间点
                            exec_expression(执行表达式)：apscheduler cron表达式或日期时间点
                        3、输出内容只能按照定时任务格式，不能有其他内容
                        
                        例子：
                        输入：今天会下雨吗？
                        输出：{}
                        
                        输入：明天早上7点叫我起床
                        输出：{"task":"起床","msg":"起床啦起床啦","task_type":"once","exec_expression":"2025-04-28 07:00:00", "tip":"好的，我将在明天早上7点提醒你起床","task_scope":"time"}
                        
                        输入：每天上午10点开会，请务必参加。
                        输出：{"task":"开会","msg":"记得开会哦","task_type":"repeat","exec_expression":"0 0 7 * * *","tip":"OK，我将在每天早上10点提醒开会","task_scope":"time"}

                        输入：明天记得叫我出门买东西
                        输出：{"task":"出门买东西","msg":"记得出门买东西，别忘了","task_type":"once","exec_expression":"2025-04-28 00:00:00", "tip":"好的，我将在明天提醒你出门买东西","task_scope":"day"}
                        
                        输入：我老婆1月22日
                        输出：{"task":"生日提醒","msg":"今天老婆生日哦","task_type":"repeat","exec_expression":"0 0 0 22 1 *","tip":"OK，我将在1月22日提醒您老婆生日","task_scope":"day"}"""
                                  )
        )

        self.role_play = RolePlay(self.ai_bot, 'remind_session', self.prompt)

        self.task_db = UserScheduleTaskDB()
        # 初始化调度器
        self.scheduler = AsyncIOScheduler()
        self.scheduler.start()

    async def on_enable(self, bot=None):
        self.wx_bot = bot
        await super().on_enable(bot)

    async def async_init(self):
        """异步初始化，加载未完成的任务"""
        await self.task_db.initialize()
        tasks = await self.task_db.get_runnable_task()
        for task in tasks:
            if task.task_type == 'repeat':
                trigger = MyCronTrigger.from_crontab(task.task_exec_expression)
            else:
                trigger = DateTrigger(run_date=task.task_exec_expression)

            self.scheduler.add_job(
                self.send_reminder,
                trigger=trigger,
                args=[self.wx_bot, task],
                id=str(task.task_id)
            )

    @on_at_message(priority=50)
    async def handle_at(self, bot: WechatAPIClient, message: dict):
        return self.handle_text(bot, message)

    @on_voice_message(priority=50)
    async def handle_voice(self, bot: WechatAPIClient, message: dict):
        text = await self.audi_ocr(bot, message)
        if text:
            message['Content'] = text
            return await self.handle_text(bot, message)
        return PLUGIN_PASS

    @on_text_message(priority=50)
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        if message.get('command', '').startswith('#') or len(message["Content"]) <= 5:
            return PLUGIN_PASS

        self.role_play.reset()
        context = Context(ContextType.TEXT, self.role_play.action(message["Content"]))
        context.kwargs = dict()
        context["session_id"] = self.role_play.sessionid
        context["gpt_model"] = self.model
        reply = self.ai_bot.reply(message["Content"], context).content
        if not reply or reply == '{}':
            return PLUGIN_PASS
        task_json = json.loads(reply)

        # {"task":"起床","msg":"起床啦起床啦","task_type":"once","exec_expression":"2025-04-23 07:00:00", "tip":"好的，我将在明天早上7点提醒你起床"}
        # {"task":"开会","msg":"记得开会哦","task_type":"repeat","exec_expression":"0 0 7 * * *","tip":"OK，我将在每天早上10点提醒开会"}
        task_type = task_json.get('task_type', '')
        if not task_type:
            return PLUGIN_PASS
        # 添加任务到调度器
        triggers = []
        tasks = []
        if task_type == 'repeat':
            triggers.append(MyCronTrigger.from_crontab(task_json.get('exec_expression')))
            tasks.append(UserScheduleTask(user_id=message['SenderWxid'],
                                          from_id=message['FromWxid'],
                                          task_name=task_json.get('task'),
                                          task_msg=task_json.get('msg'),
                                          task_type=task_type,
                                          task_exec_expression=task_json.get('exec_expression'),
                                          task_status='not_run',
                                          task_create_time=datetime.now()))
        else:
            # month/day/hour/other/time
            task_scope = task_json.get('task_scope', '')
            date_obj = datetime.strptime(task_json.get('exec_expression'), "%Y-%m-%d %H:%M:%S")
            if task_scope == 'day':
                run_dates = [
                    task_json.get('exec_expression'),
                    (date_obj + timedelta(hours=7, minutes=30)).strftime("%Y-%m-%d %H:%M:%S"),
                    (date_obj + timedelta(hours=11, minutes=30)).strftime("%Y-%m-%d %H:%M:%S"),
                    (date_obj + timedelta(hours=17, minutes=30)).strftime("%Y-%m-%d %H:%M:%S"),
                ]
            elif task_scope == 'hour':
                run_dates = [
                    task_json.get('exec_expression'),
                    (date_obj + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S"),
                ]
            else:
                run_dates = [
                    task_json.get('exec_expression')
                ]

            for rd in list(dict.fromkeys(run_dates)):
                triggers.append(DateTrigger(run_date=rd))
                tasks.append(UserScheduleTask(user_id=message['SenderWxid'],
                                              from_id=message['FromWxid'],
                                              task_name=task_json.get('task'),
                                              task_msg=task_json.get('msg'),
                                              task_type=task_type,
                                              task_exec_expression=rd,
                                              task_status='not_run',
                                              task_create_time=datetime.now()))
        for index, task in enumerate(tasks):
            if not await self.task_db.save_task(task):
                continue
            self.scheduler.add_job(
                self.send_reminder,  # 任务触发时的回调函数
                trigger=triggers[index],
                args=[bot, task],  # 传递给回调函数的参数
                id=str(task.task_id)  # 任务ID
            )
        await bot.send_reply_message(message, task_json.get('tip'))

        return PLUGIN_ENDED

    async def send_reminder(self, bot: WechatAPIClient, task: UserScheduleTask):
        """发送提醒消息"""
        at = [task.user_id] if task.from_id != task.user_id else []
        await bot.send_at_message(task.from_id, task.task_msg, at)
        # 更新任务状态
        task.task_last_exec_time = datetime.now()
        # 获取当前任务的触发器
        job = self.scheduler.get_job(str(task.task_id))
        if job:
            # 根据触发器类型判断是否有下一次执行时间
            trigger = job.trigger
            next_run_time = None

            if hasattr(trigger, "get_next_fire_time"):
                previous_fire_time = job.next_run_time
                if previous_fire_time and previous_fire_time.tzinfo is None:
                    previous_fire_time = previous_fire_time.replace(tzinfo=self.timezone)  # Use the specified timezone
                next_run_time = trigger.get_next_fire_time(previous_fire_time, datetime.now(self.timezone))
            elif hasattr(trigger, "next_run_time"):
                next_run_time = trigger.next_run_time
            # 更新任务状态
            if next_run_time:
                task.task_status = "one_completed"  # 有下一次执行时间，状态为 one_completed
                task.task_next_exec_time = next_run_time  # 更新下一次执行时间
            else:
                task.task_status = "completed"  # 没有下一次执行时间，状态为 completed
                task.task_next_exec_time = None
        else:
            task.task_status = "completed"
            task.task_next_exec_time = None

        await self.task_db.save_task(task)

    async def audi_ocr(self, bot: WechatAPIClient, message: dict) -> str:
        upload_file_id = await self.upload_file(message["FromWxid"], message["Content"])

        url = 'https://api.dify.ai/v1/workflows/run'
        headers = {"Authorization": f"Bearer app-WOBX22g8QogVRSfjOZnqAaLa", "Content-Type": "application/json"}
        payload = json.dumps({
            "inputs": {"audio": {"type": "audio", "transfer_method": "local_file", "upload_file_id": upload_file_id}},
            "user": message["FromWxid"],
            "response_mode": "blocking",
            "files": [],
        })
        async with aiohttp.ClientSession() as session:
            async with session.post(url=url, headers=headers, data=payload) as resp:
                if resp.status == 200:
                    ocr_ret = await resp.json()
                else:
                    return ''
        return ocr_ret.get('data', {}).get('outputs', {}).get('text', '')

    async def upload_file(self, user: str, file: bytes, message: dict = None):
        headers = {"Authorization": f"Bearer app-WOBX22g8QogVRSfjOZnqAaLa"}

        if message and (mime_types := mimetypes.guess_type(message["Filename"])):
            mime_type, _ = mime_types
            filename, content_type = message["Filename"], mime_type
        elif kind := filetype.guess(file):
            filename, content_type = kind.extension, kind.mime
        else:
            message = message or {}
            filename, content_type = message["Filename"], "application/octet-stream"

        formdata = aiohttp.FormData()
        formdata.add_field("user", user)
        formdata.add_field("file", file, filename=filename, content_type=content_type)

        url = "https://api.dify.ai/v1/files/upload"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=formdata) as resp:
                resp_json = await resp.json()

        return resp_json.get("id", "")


class MyCronTrigger(CronTrigger):
    @classmethod
    def from_crontab(cls, expr, timezone=None):
        values = expr.split()
        if len(values) != 6 and len(values) != 7:  # 要求7位：秒、分、时、日、月、周、年
            raise ValueError("Expected 7 fields (second to year)")
        year = values[6] if len(values) == 7 else None
        return cls(
            second=values[0], minute=values[1], hour=values[2],
            day=values[3], month=values[4], day_of_week=values[5],
            year=year, timezone=timezone
        )
