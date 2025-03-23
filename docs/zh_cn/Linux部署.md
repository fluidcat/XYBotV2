#### 1. 🔧 环境准备

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv redis-server ffmpeg

# CentOS/RHEL
sudo yum install epel-release  # 如果需要EPEL仓库
sudo yum install python3.11 redis ffmpeg
sudo systemctl start redis
sudo systemctl enable redis

# 设置 IMAGEIO_FFMPEG_EXE 环境变量
echo 'export IMAGEIO_FFMPEG_EXE=$(which ffmpeg)' >> ~/.bashrc
source ~/.bashrc

# 如果使用其他shell(如zsh)，则需要：
# echo 'export IMAGEIO_FFMPEG_EXE=$(which ffmpeg)' >> ~/.zshrc
# source ~/.zshrc
```

#### 2. ⬇️ 下载项目

```bash
# 克隆项目
git clone https://github.com/HenryXiaoYang/XYBotV2.git
# 小白：直接 Github Download ZIP

cd XYBotV2

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 安装gunicorn和eventlet
pip install gunicorn eventlet

# 使用镜像源安装
pip install -r requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
```

4. 🚀 启动机器人

```bash
# 确保在虚拟环境中
source venv/bin/activate

# 检查Redis服务状态
systemctl status redis

# 如果Redis未运行，启动服务
sudo systemctl start redis

# 设置Redis开机自启
sudo systemctl enable redis

# 验证Redis连接
redis-cli ping
# 如果返回PONG表示连接正常

# 启动机器人WebUI
python app.py
```

5. 进入WebUI

访问 `9999` 端口。

默认用户名是`admin`，密码是`admin123`

6. 点击`启动`，账号信息出会出现一个二维码，微信扫码即可。


7. 💻 不需要WebUI的简单启动方式

如果你不需要WebUI界面，可以直接使用bot.py来运行机器人：

```bash
# 确保在虚拟环境中
source venv/bin/activate

# 直接运行bot.py
python bot.py
```

这种方式不会启动Web界面，机器人核心功能依然正常工作。使用这种方式时：
- 二维码会直接显示在终端中
- 所有机器人功能正常可用


## ❓ 常见问题

1. 与网络相关的报错

- 检查网络连接，是否能ping通微信服务器
- 尝试关闭代理软件，尝试重启电脑
- 尝试重启XYBot和Redis
- 如是Docker部署，检查Docker容器网络是否能连接到微信服务器和 Redis 数据库

2. `正在运行`相关的报错

- 将占用9000端口的进程强制结束

3. 🌐 无法访问Web界面

- 确保9999端口已在防火墙中开放
```bash
# Ubuntu/Debian
sudo ufw allow 9999

# CentOS
sudo firewall-cmd --permanent --add-port=9999/tcp
sudo firewall-cmd --reload
```
