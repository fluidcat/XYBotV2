#!/bin/bash
# 启动Redis服务
redis-server /etc/redis/redis.conf --daemonize yes
# 执行主程序
exec python main.py