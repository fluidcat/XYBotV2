from WechatAPI import WechatAPIClient
from utils.config_util import loadConfig


class ScheduleMassSender:
    def __init__(self):
        config = loadConfig("main_config.toml").get('XYBot')

        self.chatroom = config.get("sch_mass_chatroom")
        self.wxid = config.get("sch_mass_wxid")
        self.all_ids = list(set(self.chatroom) | set(self.wxid))

    async def send_mass(self, bot: WechatAPIClient, msg: str):
        """
        定时群发，这里可以决定群发给谁
        """
        if not self.all_ids:
            return
        for wid in self.all_ids:
            await bot.send_text_message(wid, msg)


sch_mass_sender = ScheduleMassSender()
