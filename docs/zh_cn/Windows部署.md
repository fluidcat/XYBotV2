# 🪟 Windows 部署

## 1. 🔧 环境准备

- 安装 Python 3.11 (必须是3.11版本): https://www.python.org/downloads/release/python-3119/
    - 在安装过程中勾选 "Add Python to PATH" 选项
    - 或者手动添加：
        1. 右键点击 "此电脑" -> "属性" -> "高级系统设置" -> "环境变量"
        2. 在 "系统变量" 中找到 Path,点击 "编辑"
        3. 添加 Python 安装目录（如 `C:\Python311`）和 Scripts 目录（如 `C:\Python311\Scripts`）

- 安装 ffmpeg:
    1. 从 [ffmpeg官网](https://www.ffmpeg.org/download.html) 下载 Windows 版本
    2. 解压到合适的目录（如 `C:\ffmpeg`）
    3. 添加环境变量：
        - 右键点击 "此电脑" -> "属性" -> "高级系统设置" -> "环境变量"
        - 在 "系统变量" 中找到 Path，点击 "编辑"
        - 添加 ffmpeg 的 bin 目录路径（如 `C:\ffmpeg\bin`）
    4. 设置 IMAGEIO_FFMPEG_EXE 环境变量：
        - 在 "系统变量" 中点击 "新建"
        - 变量名输入：`IMAGEIO_FFMPEG_EXE`
        - 变量值输入 ffmpeg.exe 的完整路径（如 `C:\ffmpeg\bin\ffmpeg.exe`）
    5. 重启命令提示符或 PowerShell 使环境变量生效
    6. 验证安装：
        ```bash
        ffmpeg -version
        ```

- 安装 Redis:
    - 从 [Redis](https://github.com/tporadowski/redis/releases/tag/v5.0.14.1) 下载最新版本 (目前是7.4.2)
    - 下载并解压 `Redis-x64-5.0.14.1.zip`
    - 在命令行执行:
      ```bash
      # 进入目录
      cd Redis-x64-5.0.14.1
      
      # 启动Redis服务
      start redis-server.exe
      ```

## 2. ⬇️ 下载项目

```bash
# 克隆项目
git clone https://github.com/HenryXiaoYang/XYBotV2.git
# 小白：直接 Github Download ZIP

cd XYBotV2

# 创建虚拟环境
python -m venv venv
.\venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 安装gunicorn和eventlet
pip install gunicorn eventlet

# 使用镜像源安装
pip install -r requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
```

## 3. 🚀 启动机器人

```bash
# 确保Redis服务已启动
redis-cli ping  # 如果返回PONG则表示Redis正常运行

# 启动机器人 (新方式 - 使用gunicorn和eventlet)
python -m gunicorn --worker-class eventlet app:app --bind 0.0.0.0:9999
```

## 4. 📱 登录微信

- 扫描终端显示的二维码完成登录。如果扫不出来,可以打开二维码下面的链接扫码。
- 首次登录成功后,需要挂机4小时。之后机器人就会开始正常运行。

## 5. ⚙️ 配置文件修改

主配置: main_config.toml 主配置文件

插件配置: plugins/all_in_one_config.toml 插件配置文件

这几个插件需要配置API密钥才可正常工作:

- 🤖 Ai
- 🌤️ GetWeather


- 如果机器人正在运行，需要重启才能使主配置生效：
    ```bash
    # 按Ctrl+C停止机器人
    # 重新启动
    python -m gunicorn --worker-class eventlet app:app --bind 0.0.0.0:9999
    ```

## 6. 🔄 创建Windows服务（可选）

为了让机器人在后台运行并开机自启，可以创建Windows服务：

1. 安装NSSM（Non-Sucking Service Manager）:
   - 从 [NSSM官网](https://nssm.cc/download) 下载最新版本
   - 解压到合适的目录

2. 创建服务:
   ```bash
   # 打开管理员权限的命令提示符
   cd C:\path\to\nssm\win64
   
   # 创建服务
   nssm install XYBotV2
   ```

3. 在弹出的NSSM配置窗口中:
   - Path: `C:\XYBotV2\venv\Scripts\python.exe`
   - Startup directory: `C:\XYBotV2`
   - Arguments: `-m gunicorn --worker-class eventlet app:app --bind 0.0.0.0:9999`
   - 在Details标签中设置服务名称和描述
   - 点击"Install service"安装服务

4. 启动服务:
   ```bash
   nssm start XYBotV2
   ```

> 如果是修改插件配置则可使用热加载、热卸载、热重载指令，不用重启机器人。

## ❓ 常见问题

1. 与网络相关的报错

- 检查网络连接，是否能ping通微信服务器
- 尝试关闭代理软件，尝试重启电脑
- 尝试重启XYBot和Redis
- 如是Docker部署，检查Docker容器网络是否能连接到微信服务器和 Redis 数据库

2. `正在运行`相关的报错

- 将占用9000端口的进程强制结束

3. 🌐 无法访问Web界面

- 确保Windows防火墙允许9999端口通信
  1. 打开"控制面板" -> "Windows Defender防火墙" -> "高级设置"
  2. 选择"入站规则" -> "新建规则"
  3. 规则类型选"端口" -> 指定TCP和9999端口 -> 允许连接 -> 给规则起名并完成

## 6. 💻 不需要WebUI的简单启动方式

如果你不需要WebUI界面，可以直接使用bot.py来运行机器人：

```bash
# 确保在虚拟环境中
.\venv\Scripts\activate

# 直接运行bot.py
python bot.py
```

这种方式不会启动Web界面，机器人核心功能依然正常工作。使用这种方式时：
- 二维码会直接显示在终端中，可直接扫码登录
- 所有机器人功能正常可用
- 但没有Web管理界面，所有操作需通过聊天命令完成

> [!TIP]
> 如果只是想简单使用机器人功能，这是最轻量级的运行方式。
