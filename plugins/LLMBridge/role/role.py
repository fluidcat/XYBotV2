# encoding:utf-8

import json
import os
from loguru import logger

from WechatAPI import WechatAPIClient
from plugins.LLMBridge.bridge.bridge import Bridge


class RolePlay:
    def __init__(self, bot, sessionid, desc, wrapper=None):
        self.bot = bot
        self.sessionid = sessionid
        self.wrapper = wrapper or "%s"  # 用于包装用户输入
        self.desc = desc
        self.bot.sessions.build_session(self.sessionid, system_prompt=self.desc)

    def reset(self):
        self.bot.sessions.clear_session(self.sessionid)

    def action(self, user_action):
        session = self.bot.sessions.build_session(self.sessionid)
        if session.system_prompt != self.desc:  # 目前没有触发session过期事件，这里先简单判断，然后重置
            session.set_system_prompt(self.desc)
        prompt = self.wrapper % user_action
        return prompt


class Role:
    def __init__(self):
        super().__init__()
        curdir = os.path.dirname(__file__)
        config_path = os.path.join(curdir, "roles.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.tags = {tag: (desc, []) for tag, desc in config["tags"].items()}
                self.roles = {}
                for role in config["roles"]:
                    self.roles[role["title"].lower()] = role
                    for tag in role["tags"]:
                        if tag not in self.tags:
                            logger.warning(f"[Role] unknown tag {tag} ")
                            self.tags[tag] = (tag, [])
                        self.tags[tag][1].append(role)
                for tag in list(self.tags.keys()):
                    if len(self.tags[tag][1]) == 0:
                        logger.debug(f"[Role] no role found for tag {tag} ")
                        del self.tags[tag]

            if len(self.roles) == 0:
                raise Exception("no role found")
            self.roleplays = {}
            logger.info("[Role] inited")
        except Exception as e:
            if isinstance(e, FileNotFoundError):
                logger.warn(f"[Role] init failed, {config_path} not found, ignore or see https://github.com/zhayujie/chatgpt-on-wechat/tree/master/plugins/role .")
            else:
                logger.warn("[Role] init failed, ignore or see https://github.com/zhayujie/chatgpt-on-wechat/tree/master/plugins/role .")
            raise e

    def get_role(self, name, find_closest=True, min_sim=0.35):
        name = name.lower()
        found_role = None
        if name in self.roles:
            found_role = name
        elif find_closest:
            import difflib

            def str_simularity(a, b):
                return difflib.SequenceMatcher(None, a, b).ratio()

            max_sim = min_sim
            max_role = None
            for role in self.roles:
                sim = str_simularity(name, role)
                if sim >= max_sim:
                    max_sim = sim
                    max_role = role
            found_role = max_role
        return found_role

    async def handle_role_play(self, channel: WechatAPIClient, message: dict, session_id):
        cmd = message.get('command').split(maxsplit=1)
        cmd_args = [] if len(cmd) == 1 else cmd[1].split()
        cmd = cmd[0]

        # 特殊指令，LLMBridge的Bot内置的指令，当成聊天处理
        if cmd in ['#清除记忆', '#清除所有', '#更新配置']:
            return False

        chat_bot = Bridge().get_bot('chat')

        desckey = None
        customize = False
        trigger_prefix = '#'
        if cmd == f"{trigger_prefix}停止扮演":
            if session_id in self.roleplays:
                self.roleplays[session_id].reset()
                del self.roleplays[session_id]
            await channel.send_reply_message(message, "角色扮演结束!")
            return
        elif cmd == f"{trigger_prefix}角色":
            desckey = "descn"
        elif cmd.lower() == f"{trigger_prefix}role":
            desckey = "description"
        elif cmd == f"{trigger_prefix}设定扮演":
            customize = True
        elif cmd == f"{trigger_prefix}角色类型":
            if len(cmd_args) > 0:
                tag = cmd_args[0].strip()
                help_text = "角色列表：\n"
                for key, value in self.tags.items():
                    if value[0] == tag:
                        tag = key
                        break
                if tag == "所有":
                    for role in self.roles.values():
                        help_text += f"【{role['title']}】: {role['remark']}\n"
                elif tag in self.tags:
                    for role in self.tags[tag][1]:
                        help_text += f"】{role['title']}】: {role['remark']}\n"
                else:
                    help_text = f"未知角色类型。\n"
                    help_text += "目前的角色类型有: \n"
                    help_text += "，".join([self.tags[tag][0] for tag in self.tags]) + "\n"
            else:
                help_text = f"请输入角色类型。\n"
                help_text += "目前的角色类型有: \n"
                help_text += "，".join([self.tags[tag][0] for tag in self.tags]) + "\n"
            await channel.send_reply_message(message, help_text)
            return
        elif session_id not in self.roleplays:
            return "no_role_play"

        content = message['Content']
        # logger.debug("[Role] on_handle_context. content: %s" % content)
        if desckey is not None:
            if not cmd_args or cmd_args[0].lower() in ["help", "帮助"]:
                await channel.send_reply_message(message, self.get_help_text(verbose=True))
                return
            role = self.get_role(cmd_args[0])
            if role is None:
                await channel.send_reply_message(message, "角色不存在")
                return
            else:
                self.roleplays[session_id] = RolePlay(
                    chat_bot,
                    session_id,
                    self.roles[role][desckey],
                    self.roles[role].get("wrapper", "%s"),
                )
                await channel.send_reply_message(message, f"设置角色：{role}\n\n{self.roles[role][desckey]}\n\n停止可发送：#停止扮演")
        elif customize == True:
            self.roleplays[session_id] = RolePlay(chat_bot, session_id, cmd_args[0], "%s")
            await channel.send_reply_message(message, f"角色设定为:\n{cmd_args[0]}")
        else:
            prompt = self.roleplays[session_id].action(content)
            message["Content"] = prompt

    def get_help_text(self, verbose=False, **kwargs):
        help_text = "让机器人扮演不同的角色。\n"
        if not verbose:
            return help_text
        trigger_prefix = '#'
        help_text = f"使用方法:\n{trigger_prefix}角色" + " 预设角色名: 设定角色为{预设角色名}。\n" + f"{trigger_prefix}role" + " 预设角色名: 同上，但使用英文设定。\n"
        help_text += f"{trigger_prefix}设定扮演" + " 角色设定: 设定自定义角色人设为{角色设定}。\n"
        help_text += f"{trigger_prefix}停止扮演: 清除设定的角色。\n"
        help_text += f"{trigger_prefix}角色类型" + " 角色类型: 查看某类{角色类型}的所有预设角色，为所有时输出所有预设角色。\n"
        help_text += "\n目前的角色类型有: \n"
        help_text += "，".join([self.tags[tag][0] for tag in self.tags]) + "。\n"
        help_text += f"\n命令例子: \n{trigger_prefix}角色 写作助理\n"
        help_text += f"{trigger_prefix}角色类型 所有\n"
        help_text += f"{trigger_prefix}停止扮演\n"
        return help_text
