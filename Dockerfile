FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV TZ=Asia/Shanghai
ENV IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

# 复制 Redis 配置
COPY redis.conf /etc/redis/redis.conf

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt
# 安装gunicorn和eventlet
RUN pip install --no-cache-dir gunicorn eventlet

# 复制应用代码
COPY . .

# 创建启动脚本
RUN echo '#!/bin/bash\n\
redis-server /etc/redis/redis.conf --daemonize yes\n\
python app.py' > /app/start.sh \
    && chmod +x /app/start.sh

# 设置启动命令
CMD ["/app/start.sh"]

