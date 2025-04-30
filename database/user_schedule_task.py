import asyncio
import tomllib
from datetime import datetime
from typing import Optional

from loguru import logger
from sqlalchemy import Column, String, Integer, DateTime, select
from sqlalchemy.ext.asyncio import create_async_engine, async_scoped_session, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

from utils.singleton import Singleton

DeclarativeBase = declarative_base()


class UserScheduleTask(DeclarativeBase):
    __tablename__ = 'user_schedule_task'

    task_id = Column(Integer, primary_key=True, nullable=False, unique=True, index=True, autoincrement=True,
                     comment='task_id')
    user_id = Column(String(20), nullable=False, index=True, comment='user_id')
    from_id = Column(String(20), nullable=False, index=True, comment='from_id')
    task_name = Column(String(255), nullable=False, comment='task_name')
    task_msg = Column(String(1024), comment='task_msg')
    task_type = Column(String(20), nullable=False, comment='task_type')
    task_status = Column(String(8), nullable=False, index=True, default='no_run', comment='task_status')
    task_exec_expression = Column(String(32), nullable=False, comment='task_exec_expression')
    task_create_time = Column(DateTime, nullable=False, default=datetime.now(), comment='task_create_time')
    task_next_exec_time = Column(DateTime, comment='task_next_exec_time')
    task_last_exec_time = Column(DateTime, comment='task_last_exec_time')


class UserScheduleTaskDB(metaclass=Singleton):
    _instance = None

    def __new__(cls):
        with open("main_config.toml", "rb") as f:
            main_config = tomllib.load(f)
        db_url = main_config["XYBot"]["userScheduleTaskDB-url"]

        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.engine = create_async_engine(
                db_url,
                echo=False,
                future=True
            )
            cls._async_session_factory = async_scoped_session(
                sessionmaker(
                    cls._instance.engine,
                    class_=AsyncSession,
                    expire_on_commit=False
                ),
                scopefunc=asyncio.current_task
            )
        return cls._instance

    async def initialize(self):
        """异步初始化数据库"""
        async with self.engine.begin() as conn:
            await conn.run_sync(DeclarativeBase.metadata.create_all)

    async def save_task(self,
                        task: Optional[UserScheduleTask],
                        user_id: str = None,
                        from_id: str = None,
                        task_name: str = None,
                        task_type: str = None,
                        task_msg: Optional[str] = None,
                        task_status: str = None,
                        task_exec_expression: str = None
                        ):
        async with self._async_session_factory() as session:
            try:
                if task is None:
                    # 新增任务
                    new_task = UserScheduleTask(
                        user_id=user_id,
                        from_id=from_id,
                        task_name=task_name,
                        task_type=task_type,
                        task_msg=task_msg,
                        task_status=task_status,
                        task_exec_expression=task_exec_expression,
                        task_create_time=datetime.now()
                    )
                    session.add(new_task)
                else:
                    # 更新任务
                    if user_id is not None:
                        task.user_id = user_id
                    if from_id is not None:
                        task.from_id = from_id
                    if task_name is not None:
                        task.task_name = task_name
                    if task_type is not None:
                        task.task_type = task_type
                    if task_msg is not None:
                        task.task_msg = task_msg
                    if task_status is not None:
                        task.task_status = task_status
                    if task_exec_expression is not None:
                        task.task_exec_expression = task_exec_expression
                    task.task_last_exec_time = datetime.now()  # 更新最后执行时间
                    session.add(task)

                await session.commit()
                return True
            except Exception as e:
                logger.error(f"保存或更新任务失败: {str(e)}")
                await session.rollback()
                return False

    async def get_runnable_task(self) -> list[UserScheduleTask]:
        """
        获取状态为 not_run 或 one_completed 的任务。

        :return: 符合条件的任务列表
        """
        async with self._async_session_factory() as session:
            result = await session.execute(
                select(UserScheduleTask)
                .where(UserScheduleTask.task_status.in_(["not_run", "one_completed"]))
            )
            tasks = result.scalars().all()
            return tasks


