from WechatAPI import WechatAPIClient


async def send_mass(bot: WechatAPIClient, msg: str):
    chatroom = ['24233177454@chatroom']
    wxid = []

    all_ids = list(set(chatroom) | set(wxid))
    if not all_ids:
        return
    for wid in list(set(chatroom) | set(wxid)):
        await bot.send_text_message(wid, msg)

