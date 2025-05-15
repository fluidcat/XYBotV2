"""
依赖包管理插件 - 允许管理员通过微信命令安装Python依赖包和Github插件

作者: 老夏的金库
版本: 1.2.0
"""
import importlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile

import requests
from loguru import logger

from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.plugin_base import PluginBase


class DependencyManager(PluginBase):
    """依赖包管理插件，允许管理员通过微信发送命令来安装/更新/查询Python依赖包和Github插件"""

    description = "依赖包管理插件"
    author = "老夏的金库 HenryXiaoYang"
    version = "1.2.0"

    # Change Log
    # 1.2.0 HenryXiaoYang 把调试消息和日志都注释掉了，因为刷屏有点严重

    def __init__(self):
        super().__init__()

        # 记录插件开始初始化
        # logger.info("[DependencyManager] 开始加载插件")

        # 获取配置文件路径
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(self.plugin_dir, "config.toml")

        # 获取主项目根目录 - 使用相对路径 - _data/plugins
        self.root_dir = os.path.dirname(self.plugin_dir)  # 指向_data/plugins目录
        # logger.info(f"[DependencyManager] 根目录设置为: {self.root_dir}")

        # 插件目录就是根目录本身
        self.plugins_dir = self.root_dir
        # logger.info(f"[DependencyManager] 插件目录设置为: {self.plugins_dir}")

        # 加载配置
        self.load_config()

        # logger.info(f"[DependencyManager] 插件初始化完成, 启用状态: {self.enable}, 优先级: 80")

    def load_config(self):
        """加载配置文件"""
        try:
            with open("main_config.toml", "rb") as f:
                config = tomllib.load(f)

            self.admin_list = config.get("XYBot", {}).get("admins", [])

            # logger.info(f"[DependencyManager] 尝试从 {self.config_path} 加载配置")

            with open(self.config_path, "rb") as f:
                config = tomllib.load(f)

            # 读取基本配置
            basic_config = config.get("basic", {})
            self.enable = basic_config.get("enable", False)
            self.allowed_packages = basic_config.get("allowed_packages", [])
            self.check_allowed = basic_config.get("check_allowed", False)

            # 读取命令配置
            cmd_config = config.get("commands", {})
            self.install_cmd = cmd_config.get("install", "!pip install")
            self.show_cmd = cmd_config.get("show", "!pip show")
            self.list_cmd = cmd_config.get("list", "!pip list")
            self.uninstall_cmd = cmd_config.get("uninstall", "!pip uninstall")

            # 读取插件安装配置 - 使用唤醒词
            self.github_install_prefix = cmd_config.get("github_install", "github")

            # logger.info(f"[DependencyManager] 配置加载成功")
            # logger.info(f"[DependencyManager] 启用状态: {self.enable}")
            # logger.info(f"[DependencyManager] 管理员列表: {self.admin_list}")
            logger.info(f"[DependencyManager] GitHub前缀: '{self.github_install_prefix}'")

        except Exception as e:
            logger.error(f"[DependencyManager] 加载配置失败: {str(e)}")
            self.enable = False
            self.admin_list = []
            self.allowed_packages = []
            self.check_allowed = False
            self.install_cmd = "!pip install"
            self.show_cmd = "!pip show"
            self.list_cmd = "!pip list"
            self.uninstall_cmd = "!pip uninstall"
            self.github_install_prefix = "github"

    @on_text_message(priority=80)
    async def handle_text_message(self, bot: WechatAPIClient, message: dict):
        """处理文本消息，检查是否为依赖管理命令"""
        # 在最开始就记录收到消息，即使未启用也记录，便于调试
        # logger.info(f"[DependencyManager] 收到消息调用: {message.get('Content', '')}")

        if not self.enable:
            # logger.debug("[DependencyManager] 插件未启用，跳过处理")
            return True  # 插件未启用，允许其他插件处理

        # 获取消息内容和发送者 - 修改为使用正确的键名
        content = message.get("Content", "").strip()
        from_user = message.get("SenderWxid", "")
        conversation_id = message.get("FromWxid", "")

        # 记录所有消息，用于调试
        # logger.info(f"[DependencyManager] 收到消息: '{content}'")

        # 检查是否为管理员
        sender_id = from_user
        # if not sender_id and "IsGroup" in message and message["IsGroup"]:
        # 如果是群聊消息，则SenderWxid应该已经包含发送者ID
        # logger.debug(f"[DependencyManager] 群消息，发送者ID: {sender_id}")

        # 记录消息处理信息
        # logger.info(f"[DependencyManager] 发送者ID: {sender_id}")
        # logger.info(f"[DependencyManager] 会话ID: {conversation_id}")
        # logger.info(f"[DependencyManager] GitHub安装前缀: {self.github_install_prefix}")

        # 检查是否为管理员
        if sender_id not in self.admin_list:
            # logger.info(f"[DependencyManager] 用户 {sender_id} 不在管理员列表中")
            # logger.info(f"[DependencyManager] 当前管理员列表: {self.admin_list}")
            return True  # 非管理员，允许其他插件处理

        # logger.info(f"[DependencyManager] 管理员 {sender_id} 发送命令: {content}")

        # ====================== 命令处理部分 ======================
        # 按照优先级排序，先处理特殊命令，再处理标准命令模式

        # 1. 测试命令 - 用于诊断插件是否正常工作
        if content == "!test dm":
            await bot.send_text_message(conversation_id, "✅ DependencyManager插件工作正常！")
            logger.info("[DependencyManager] 测试命令响应成功")
            return False

        # 2. GitHub相关命令处理 - 优先级最高

        # 2.1 检查是否明确以GitHub前缀开头 - 要求明确的安装意图
        starts_with_prefix = content.lower().startswith(self.github_install_prefix.lower())
        # logger.info(
        #     f"[DependencyManager] 检查是否以'{self.github_install_prefix}'开头: {starts_with_prefix}, 内容: '{content}'")

        # 2.2 GitHub快捷命令 - GeminiImage特殊处理
        if starts_with_prefix and (content.strip().lower() == f"{self.github_install_prefix} gemini" or
                                   content.strip().lower() == f"{self.github_install_prefix} geminiimage"):
            logger.info("[DependencyManager] 检测到GeminiImage快捷安装命令")
            await bot.send_text_message(conversation_id, "🔄 正在安装GeminiImage插件...")
            await self._handle_github_install(bot, conversation_id, "https://github.com/NanSsye/GeminiImage.git")
            logger.info("[DependencyManager] GeminiImage快捷安装完成，阻止后续插件处理")
            return False

        # 2.3 GitHub帮助命令
        if content.strip().lower() == f"{self.github_install_prefix} help":
            help_text = f"""📦 GitHub插件安装帮助:

1. 安装GitHub上的插件:
   {self.github_install_prefix} https://github.com/用户名/插件名.git

2. 例如，安装GeminiImage插件:
   {self.github_install_prefix} https://github.com/NanSsye/GeminiImage.git
   
3. 简化格式:
   {self.github_install_prefix} 用户名/插件名
   
4. 快捷命令安装GeminiImage:
   {self.github_install_prefix} gemini

5. 插件会自动被克隆到插件目录并安装依赖

注意: 安装后需要重启机器人以加载新插件。
"""
            await bot.send_text_message(conversation_id, help_text)
            logger.info("[DependencyManager] GitHub安装帮助命令响应成功")
            return False

        # 2.4 标准GitHub安装命令处理 - 必须以明确的前缀开头
        if starts_with_prefix:
            logger.info(f"[DependencyManager] 检测到GitHub安装命令: {content}")
            # 获取前缀后面的内容
            command_content = content[len(self.github_install_prefix):].strip()
            logger.info(f"[DependencyManager] 提取的命令内容: '{command_content}'")

            # 处理快捷命令 - gemini
            if command_content.lower() == "gemini" or command_content.lower() == "geminiimage":
                logger.info("[DependencyManager] 检测到GeminiImage快捷安装命令")
                await self._handle_github_install(bot, conversation_id, "https://github.com/NanSsye/GeminiImage.git")
                logger.info("[DependencyManager] GeminiImage安装命令处理完成，返回False阻止后续处理")
                return False

            # 处理标准GitHub URL
            elif command_content.startswith("https://github.com") or command_content.startswith("github.com"):
                logger.info(f"[DependencyManager] 检测到GitHub URL: {command_content}")
                await self._handle_github_install(bot, conversation_id, command_content)
                logger.info("[DependencyManager] GitHub URL安装命令处理完成，返回False阻止后续处理")
                return False

            # 处理简化格式 - 用户名/仓库名
            elif "/" in command_content and not command_content.startswith("!"):
                # 检查是否符合 用户名/仓库名 格式
                if re.match(r'^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$', command_content.strip()):
                    repo_path = command_content.strip()
                    logger.info(f"[DependencyManager] 检测到简化的GitHub路径: {repo_path}")
                    github_url = f"https://github.com/{repo_path}"
                    logger.info(f"[DependencyManager] 构建GitHub URL: {github_url}")
                    await self._handle_github_install(bot, conversation_id, github_url)
                    logger.info("[DependencyManager] 简化GitHub路径安装命令处理完成，返回False阻止后续处理")
                    return False

            # 格式不正确
            else:
                await bot.send_text_message(conversation_id,
                                            f"⚠️ GitHub安装命令格式不正确。正确格式为: \n1. {self.github_install_prefix} https://github.com/用户名/插件名.git\n2. {self.github_install_prefix} 用户名/插件名")
                logger.info("[DependencyManager] GitHub格式不正确，已发送提示，返回False阻止后续处理")
                return False

            # 如果是以GitHub前缀开头但没有匹配到任何处理分支，也阻止后续处理
            logger.info("[DependencyManager] 命令以github开头但未匹配任何处理逻辑，默认阻止后续处理")
            return False

        # 忽略智能识别GitHub URL的逻辑，必须以明确的前缀开始才处理

        # 3. 依赖管理命令

        # 3.1 处理安装命令
        if content.startswith(self.install_cmd):
            await self._handle_install(bot, conversation_id, content.replace(self.install_cmd, "").strip())
            logger.debug(f"[DependencyManager] 处理安装命令完成，阻止后续插件")
            return False  # 命令已处理，不传递给其他插件

        # 3.2 处理查询命令
        elif content.startswith(self.show_cmd):
            await self._handle_show(bot, conversation_id, content.replace(self.show_cmd, "").strip())
            logger.debug(f"[DependencyManager] 处理查询命令完成，阻止后续插件")
            return False

        # 3.3 处理列表命令
        elif content.startswith(self.list_cmd):
            await self._handle_list(bot, conversation_id)
            logger.debug(f"[DependencyManager] 处理列表命令完成，阻止后续插件")
            return False

        # 3.4 处理卸载命令
        elif content.startswith(self.uninstall_cmd):
            await self._handle_uninstall(bot, conversation_id, content.replace(self.uninstall_cmd, "").strip())
            logger.debug(f"[DependencyManager] 处理卸载命令完成，阻止后续插件")
            return False

        # 3.5 处理帮助命令
        elif content.strip() == "!pip help" or content.strip() == "!pip":
            await self._send_help(bot, conversation_id)
            logger.debug(f"[DependencyManager] 处理帮助命令完成，阻止后续插件")
            return False

        # 3.6 处理导入检查命令
        elif content.startswith("!import"):
            package = content.replace("!import", "").strip()
            await self._check_import(bot, conversation_id, package)
            logger.debug(f"[DependencyManager] 处理导入检查命令完成，阻止后续插件")
            return False

        # 不是本插件的命令
        # logger.debug(f"[DependencyManager] 非依赖管理相关命令，允许其他插件处理")
        return True  # 不是命令，允许其他插件处理

    async def _handle_install(self, bot: WechatAPIClient, chat_id: str, package_spec: str):
        """处理安装依赖包命令"""
        if not package_spec:
            await bot.send_text_message(chat_id, "请指定要安装的包，例如: !pip install packagename==1.0.0")
            return

        # 检查是否在允许安装的包列表中
        base_package = package_spec.split("==")[0].split(">=")[0].split(">")[0].split("<")[0].strip()
        if self.check_allowed and self.allowed_packages and base_package not in self.allowed_packages:
            await bot.send_text_message(chat_id, f"⚠️ 安全限制: {base_package} 不在允许安装的包列表中")
            return

        await bot.send_text_message(chat_id, f"📦 正在安装: {package_spec}...")

        try:
            # 执行pip安装命令
            process = subprocess.Popen(
                [sys.executable, "-m", "pip", "install", package_spec],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                # 安装成功
                output = f"✅ 安装成功: {package_spec}\n\n{stdout}"
                # 如果输出太长，只取前后部分
                if len(output) > 1000:
                    output = output[:500] + "\n...\n" + output[-500:]
                await bot.send_text_message(chat_id, output)
            else:
                # 安装失败
                error = f"❌ 安装失败: {package_spec}\n\n{stderr}"
                # 如果输出太长，只取前后部分
                if len(error) > 1000:
                    error = error[:500] + "\n...\n" + error[-500:]
                await bot.send_text_message(chat_id, error)

        except Exception as e:
            await bot.send_text_message(chat_id, f"❌ 执行安装命令时出错: {str(e)}")

    async def _handle_github_install(self, bot: WechatAPIClient, chat_id: str, github_url: str):
        """处理从Github安装插件的命令"""
        logger.info(f"[DependencyManager] 开始处理GitHub插件安装，URL: {github_url}")

        # 处理各种GitHub URL格式
        if not github_url:
            logger.warning("[DependencyManager] GitHub URL为空")
            await bot.send_text_message(chat_id,
                                        "请提供有效的GitHub仓库URL，例如: github https://github.com/用户名/插件名.git")
            return

        # 标准化GitHub URL
        # 处理不包含https://的情况
        if not github_url.startswith("http"):
            if github_url.startswith("github.com"):
                github_url = "https://" + github_url
            elif "github.com" in github_url:
                # 尝试提取用户名/仓库名
                match = re.search(r'(?:github\.com[:/])?([^/\s]+/[^/\s]+)(?:\.git)?', github_url)
                if match:
                    repo_path = match.group(1)
                    github_url = f"https://github.com/{repo_path}"
                else:
                    github_url = "https://github.com/" + github_url.strip()

        logger.info(f"[DependencyManager] 标准化后的URL: {github_url}")

        # 验证URL格式
        if not github_url.startswith("https://github.com"):
            logger.warning(f"[DependencyManager] 无效的GitHub URL: {github_url}")
            await bot.send_text_message(chat_id,
                                        "请提供有效的GitHub仓库URL，例如: github https://github.com/用户名/插件名.git")
            return

        # 确保URL以.git结尾
        if github_url.endswith(".git"):
            github_url = github_url[:-4]  # 移除.git后缀，为了构建zip下载链接

        # 从URL提取插件名称和仓库信息
        repo_match = re.search(r'https://github\.com/([^/]+)/([^/]+)$', github_url)
        if not repo_match:
            logger.warning(f"[DependencyManager] 无法从URL中提取仓库信息: {github_url}")
            await bot.send_text_message(chat_id, f"⚠️ 无法从URL中提取仓库信息: {github_url}")
            return

        user_name = repo_match.group(1)
        repo_name = repo_match.group(2)
        plugin_name = repo_name

        # 使用相对路径，直接在plugins_dir下创建插件目录
        plugin_target_dir = os.path.join(self.plugins_dir, plugin_name)
        logger.info(f"[DependencyManager] 提取到用户名: {user_name}, 仓库名: {repo_name}")
        logger.info(f"[DependencyManager] 目标目录: {plugin_target_dir}")

        # 检查插件目录是否已存在
        if os.path.exists(plugin_target_dir):
            logger.info(f"[DependencyManager] 插件目录已存在，尝试更新")
            await bot.send_text_message(chat_id, f"⚠️ 插件 {plugin_name} 目录已存在，尝试更新...")
            try:
                # 尝试使用git更新现有插件
                git_installed = self._check_git_installed()
                if git_installed:
                    os.chdir(plugin_target_dir)
                    logger.info(f"[DependencyManager] 执行git pull操作于: {plugin_target_dir}")
                    process = subprocess.Popen(
                        ["git", "pull", "origin", "main"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    stdout, stderr = process.communicate()
                    logger.info(f"[DependencyManager] Git pull结果：退出码 {process.returncode}")
                    logger.info(f"[DependencyManager] Stdout: {stdout}")
                    logger.info(f"[DependencyManager] Stderr: {stderr}")

                    if process.returncode == 0:
                        await bot.send_text_message(chat_id, f"✅ 成功更新插件 {plugin_name}!\n\n{stdout}")
                        await self._install_plugin_requirements(bot, chat_id, plugin_target_dir)
                    else:
                        logger.error(f"[DependencyManager] 更新插件失败: {stderr}")
                        await bot.send_text_message(chat_id, f"❌ 更新插件失败: {stderr}")
                else:
                    # 使用ZIP方式更新
                    await bot.send_text_message(chat_id, f"⚠️ Git未安装，尝试通过下载ZIP方式更新...")
                    success = await self._download_github_zip(bot, chat_id, user_name, repo_name, plugin_target_dir,
                                                              is_update=True)
                    if success:
                        await self._install_plugin_requirements(bot, chat_id, plugin_target_dir)
            except Exception as e:
                logger.exception(f"[DependencyManager] 更新插件时出错")
                await bot.send_text_message(chat_id, f"❌ 更新插件时出错: {str(e)}")
            return

        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                logger.info(f"[DependencyManager] 创建临时目录: {temp_dir}")
                await bot.send_text_message(chat_id, f"🔄 正在从GitHub下载插件 {plugin_name}...")

                # 检查git是否安装，决定使用哪种下载方式
                git_installed = self._check_git_installed()
                logger.info(f"[DependencyManager] Git命令安装状态: {git_installed}")

                if git_installed:
                    # 使用git克隆仓库
                    logger.info(f"[DependencyManager] 使用git克隆: {github_url}.git 到 {temp_dir}")
                    process = subprocess.Popen(
                        ["git", "clone", f"{github_url}.git", temp_dir],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    stdout, stderr = process.communicate()
                    logger.info(f"[DependencyManager] Git clone结果：退出码 {process.returncode}")
                    logger.info(f"[DependencyManager] Stdout: {stdout}")
                    logger.info(f"[DependencyManager] Stderr: {stderr}")

                    if process.returncode != 0:
                        logger.error(f"[DependencyManager] Git克隆失败，尝试使用ZIP方式下载")
                        success = await self._download_github_zip(bot, chat_id, user_name, repo_name, temp_dir)
                        if not success:
                            return
                else:
                    # 使用ZIP方式下载
                    logger.info(f"[DependencyManager] Git未安装，使用ZIP方式下载")
                    success = await self._download_github_zip(bot, chat_id, user_name, repo_name, temp_dir)
                    if not success:
                        return

                # 克隆或下载成功，复制到插件目录
                logger.info(f"[DependencyManager] 创建插件目录: {plugin_target_dir}")
                os.makedirs(plugin_target_dir, exist_ok=True)

                # 复制所有文件
                logger.info(f"[DependencyManager] 开始从临时目录复制文件到插件目录")
                for item in os.listdir(temp_dir):
                    s = os.path.join(temp_dir, item)
                    d = os.path.join(plugin_target_dir, item)
                    logger.info(f"[DependencyManager] 复制: {s} 到 {d}")
                    if os.path.isdir(s):
                        shutil.copytree(s, d, dirs_exist_ok=True)
                    else:
                        shutil.copy2(s, d)

                logger.info(f"[DependencyManager] 文件复制完成")
                await bot.send_text_message(chat_id, f"✅ 成功下载插件 {plugin_name}!")

                # 安装依赖
                await self._install_plugin_requirements(bot, chat_id, plugin_target_dir)
            except Exception as e:
                logger.exception(f"[DependencyManager] 安装插件时出错")
                await bot.send_text_message(chat_id, f"❌ 安装插件时出错: {str(e)}")

    def _check_git_installed(self):
        """检查git命令是否可用"""
        try:
            process = subprocess.Popen(
                ["git", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            process.communicate()
            return process.returncode == 0
        except Exception:
            return False

    async def _download_github_zip(self, bot, chat_id, user_name, repo_name, target_dir, is_update=False):
        """使用requests下载GitHub仓库的ZIP文件"""
        try:
            # 构建ZIP下载链接
            zip_url = f"https://github.com/{user_name}/{repo_name}/archive/refs/heads/main.zip"
            logger.info(f"[DependencyManager] 开始下载ZIP: {zip_url}")

            # 发送下载状态
            await bot.send_text_message(chat_id, f"📥 正在从GitHub下载ZIP文件: {zip_url}")

            # 下载ZIP文件
            response = requests.get(zip_url, timeout=30)
            if response.status_code != 200:
                # 尝试使用master分支
                zip_url = f"https://github.com/{user_name}/{repo_name}/archive/refs/heads/master.zip"
                logger.info(f"[DependencyManager] 尝试下载master分支: {zip_url}")
                response = requests.get(zip_url, timeout=30)

            if response.status_code != 200:
                logger.error(f"[DependencyManager] 下载ZIP失败，状态码: {response.status_code}")
                await bot.send_text_message(chat_id, f"❌ 下载ZIP文件失败，HTTP状态码: {response.status_code}")
                return False

            # 解压ZIP文件
            logger.info(f"[DependencyManager] 下载完成，文件大小: {len(response.content)} 字节")
            logger.info(f"[DependencyManager] 解压ZIP文件到: {target_dir}")

            z = zipfile.ZipFile(io.BytesIO(response.content))

            # 检查ZIP文件内容
            zip_contents = z.namelist()
            logger.info(f"[DependencyManager] ZIP文件内容: {', '.join(zip_contents[:5])}...")

            if is_update:
                # 更新时先备份配置文件
                config_files = []
                if os.path.exists(os.path.join(target_dir, "config.toml")):
                    with open(os.path.join(target_dir, "config.toml"), "rb") as f:
                        config_files.append(("config.toml", f.read()))

                # 清空目录（保留.git目录）
                for item in os.listdir(target_dir):
                    if item == ".git":
                        continue
                    item_path = os.path.join(target_dir, item)
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)

            # 解压文件
            extract_dir = tempfile.mkdtemp()
            z.extractall(extract_dir)

            # ZIP文件解压后通常会有一个包含所有文件的顶级目录
            extracted_dirs = os.listdir(extract_dir)
            if len(extracted_dirs) == 1:
                extract_subdir = os.path.join(extract_dir, extracted_dirs[0])

                # 将文件从解压的子目录复制到目标目录
                for item in os.listdir(extract_subdir):
                    s = os.path.join(extract_subdir, item)
                    d = os.path.join(target_dir, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d, dirs_exist_ok=True)
                    else:
                        shutil.copy2(s, d)
            else:
                # 直接解压到目标目录
                for item in os.listdir(extract_dir):
                    s = os.path.join(extract_dir, item)
                    d = os.path.join(target_dir, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d, dirs_exist_ok=True)
                    else:
                        shutil.copy2(s, d)

            # 清理临时目录
            shutil.rmtree(extract_dir)

            # 如果是更新，恢复配置文件
            if is_update and config_files:
                for filename, content in config_files:
                    with open(os.path.join(target_dir, filename), "wb") as f:
                        f.write(content)
                logger.info(f"[DependencyManager] 已恢复配置文件")

            await bot.send_text_message(chat_id, f"✅ ZIP文件下载并解压成功")
            return True
        except Exception as e:
            logger.exception(f"[DependencyManager] 下载ZIP文件时出错")
            await bot.send_text_message(chat_id, f"❌ 下载ZIP文件时出错: {str(e)}")
            return False

    async def _install_plugin_requirements(self, bot: WechatAPIClient, chat_id: str, plugin_dir: str):
        """安装插件的依赖项"""
        requirements_file = os.path.join(plugin_dir, "requirements.txt")

        if not os.path.exists(requirements_file):
            await bot.send_text_message(chat_id, "📌 未找到requirements.txt文件，跳过依赖安装")
            return

        try:
            await bot.send_text_message(chat_id, "📦 正在安装插件依赖...")

            # 读取requirements.txt内容
            with open(requirements_file, "r") as f:
                requirements = f.read()

            # 显示依赖列表
            await bot.send_text_message(chat_id, f"📋 依赖列表:\n{requirements}")

            # 安装依赖
            process = subprocess.Popen(
                [sys.executable, "-m", "pip", "install", "-r", requirements_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                output = f"✅ 依赖安装成功!\n\n{stdout}"
                # 如果输出太长，只取前后部分
                if len(output) > 1000:
                    output = output[:500] + "\n...\n" + output[-500:]
                await bot.send_text_message(chat_id, output)

                # 提示重启机器人
                await bot.send_text_message(chat_id, "🔄 插件安装完成！请重启机器人以加载新插件。")
            else:
                error = f"❌ 依赖安装失败:\n\n{stderr}"
                # 如果输出太长，只取前后部分
                if len(error) > 1000:
                    error = error[:500] + "\n...\n" + error[-500:]
                await bot.send_text_message(chat_id, error)
        except Exception as e:
            await bot.send_text_message(chat_id, f"❌ 安装依赖时出错: {str(e)}")

    async def _handle_show(self, bot: WechatAPIClient, chat_id: str, package: str):
        """处理查询包信息命令"""
        if not package:
            await bot.send_text_message(chat_id, "请指定要查询的包，例如: !pip show packagename")
            return

        await bot.send_text_message(chat_id, f"🔍 正在查询: {package}...")

        try:
            process = subprocess.Popen(
                [sys.executable, "-m", "pip", "show", package],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                # 查询成功
                await bot.send_text_message(chat_id, f"📋 {package} 信息:\n\n{stdout}")
            else:
                # 查询失败
                await bot.send_text_message(chat_id, f"❌ 查询失败: {package}\n\n{stderr}")

        except Exception as e:
            await bot.send_text_message(chat_id, f"❌ 执行查询命令时出错: {str(e)}")

    async def _handle_list(self, bot: WechatAPIClient, chat_id: str):
        """处理列出所有包命令"""
        await bot.send_text_message(chat_id, "📋 正在获取已安装的包列表...")

        try:
            process = subprocess.Popen(
                [sys.executable, "-m", "pip", "list"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                # 获取成功，但可能很长，分段发送
                if len(stdout) > 1000:
                    chunks = [stdout[i:i + 1000] for i in range(0, len(stdout), 1000)]
                    await bot.send_text_message(chat_id, f"📦 已安装的包列表 (共{len(chunks)}段):")
                    for i, chunk in enumerate(chunks):
                        await bot.send_text_message(chat_id, f"📦 第{i + 1}段:\n\n{chunk}")
                else:
                    await bot.send_text_message(chat_id, f"📦 已安装的包列表:\n\n{stdout}")
            else:
                # 获取失败
                await bot.send_text_message(chat_id, f"❌ 获取列表失败\n\n{stderr}")

        except Exception as e:
            await bot.send_text_message(chat_id, f"❌ 执行列表命令时出错: {str(e)}")

    async def _handle_uninstall(self, bot: WechatAPIClient, chat_id: str, package: str):
        """处理卸载包命令"""
        if not package:
            await bot.send_text_message(chat_id, "请指定要卸载的包，例如: !pip uninstall packagename")
            return

        await bot.send_text_message(chat_id, f"🗑️ 正在卸载: {package}...")

        try:
            # 使用-y参数自动确认卸载
            process = subprocess.Popen(
                [sys.executable, "-m", "pip", "uninstall", "-y", package],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                # 卸载成功
                await bot.send_text_message(chat_id, f"✅ 卸载成功: {package}\n\n{stdout}")
            else:
                # 卸载失败
                await bot.send_text_message(chat_id, f"❌ 卸载失败: {package}\n\n{stderr}")

        except Exception as e:
            await bot.send_text_message(chat_id, f"❌ 执行卸载命令时出错: {str(e)}")

    async def _send_help(self, bot: WechatAPIClient, chat_id: str):
        """发送帮助信息"""
        help_text = f"""📚 依赖包管理插件使用帮助:

1️⃣ 安装包:
   {self.install_cmd} package_name
   {self.install_cmd} package_name==1.2.3  (指定版本)

2️⃣ 查询包信息:
   {self.show_cmd} package_name

3️⃣ 列出所有已安装的包:
   {self.list_cmd}

4️⃣ 卸载包:
   {self.uninstall_cmd} package_name

5️⃣ 检查包是否可以导入:
   !import package_name

6️⃣ 安装GitHub插件:
   {self.github_install_prefix} https://github.com/用户名/插件名.git

ℹ️ 仅允许管理员使用此功能
"""
        await bot.send_text_message(chat_id, help_text)

    async def _check_import(self, bot: WechatAPIClient, chat_id: str, package: str):
        """检查包是否可以成功导入"""
        if not package:
            await bot.send_text_message(chat_id, "请指定要检查的包，例如: !import packagename")
            return

        await bot.send_text_message(chat_id, f"🔍 正在检查是否可以导入: {package}...")

        try:
            # 尝试导入包
            importlib.import_module(package)
            await bot.send_text_message(chat_id, f"✅ {package} 可以成功导入!")
        except ImportError as e:
            await bot.send_text_message(chat_id, f"❌ 无法导入 {package}: {str(e)}")
        except Exception as e:
            await bot.send_text_message(chat_id, f"❌ 导入 {package} 时发生错误: {str(e)}")

    async def on_disable(self):
        """插件禁用时的清理工作"""
        await super().on_disable()
        logger.info("[DependencyManager] 插件已禁用")
