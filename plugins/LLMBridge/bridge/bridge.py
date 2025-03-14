from plugins.LLMBridge.bot.bot_factory import create_bot
from plugins.LLMBridge.bridge.context import Context
from plugins.LLMBridge.bridge.reply import Reply
from plugins.LLMBridge.common import const
from plugins.LLMBridge.common.log import logger
from plugins.LLMBridge.common.singleton import singleton
from plugins.LLMBridge.LLMBridge_config import conf
from plugins.LLMBridge.translate.factory import create_translator
from plugins.LLMBridge.voice.factory import create_voice


@singleton
class Bridge(object):
    def __init__(self):
        self.btype = {
            "chat": const.CHATGPT,
            "voice_to_text": conf().get("voice_to_text", "openai"),
            "text_to_voice": conf().get("text_to_voice", "google"),
            "translate": conf().get("translate", "baidu"),
        }
        # 这边取配置的模型
        bot_type = conf().get("bot_type")
        if bot_type:
            self.btype["chat"] = bot_type
        else:
            model_type = conf().get("model") or const.GPT35
            self.btype["chat"] = self.infer_bot_type(model_type)

            if conf().get("use_linkai") and conf().get("linkai_api_key"):
                if not conf().get("voice_to_text") or conf().get("voice_to_text") in ["openai"]:
                    self.btype["voice_to_text"] = const.LINKAI
                if not conf().get("text_to_voice") or conf().get("text_to_voice") in ["openai", const.TTS_1, const.TTS_1_HD]:
                    self.btype["text_to_voice"] = const.LINKAI

        self.bots = {}
        self.chat_bots = {}

    def infer_bot_type(self, model_type):
        bot_type = const.CHATGPT
        if model_type in ["text-davinci-003"]:
            bot_type = const.OPEN_AI
        if conf().get("use_azure_chatgpt", False):
            bot_type = const.CHATGPTONAZURE
        if model_type in ["wenxin", "wenxin-4"]:
            bot_type = const.BAIDU
        if model_type in ["xunfei"]:
            bot_type = const.XUNFEI
        if model_type in [const.QWEN]:
            bot_type = const.QWEN
        if model_type in [const.QWEN_TURBO, const.QWEN_PLUS, const.QWEN_MAX]:
            bot_type = const.QWEN_DASHSCOPE
        if model_type and model_type.startswith("gemini"):
            bot_type = const.GEMINI
        if model_type and model_type.startswith("glm"):
            bot_type = const.ZHIPU_AI
        if model_type and model_type.startswith("claude-3"):
            bot_type = const.CLAUDEAPI

        if model_type in ["claude"]:
            bot_type = const.CLAUDEAI

        if model_type in [const.MOONSHOT, "moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"]:
            bot_type = const.MOONSHOT

        if model_type in ["abab6.5-chat"]:
            bot_type = const.MiniMax

        if conf().get("use_linkai") and conf().get("linkai_api_key"):
            bot_type = const.LINKAI

        return bot_type

    # 模型对应的接口
    def get_bot(self, typename):
        if self.bots.get(typename) is None:
            logger.info("create bot {} for {}".format(self.btype[typename], typename))
            if typename == "text_to_voice":
                self.bots[typename] = create_voice(self.btype[typename])
            elif typename == "voice_to_text":
                self.bots[typename] = create_voice(self.btype[typename])
            elif typename == "chat":
                self.bots[typename] = create_bot(self.btype[typename])
            elif typename == "translate":
                self.bots[typename] = create_translator(self.btype[typename])
        return self.bots[typename]

    def get_bot_type(self, typename):
        return self.btype[typename]

    def fetch_reply_content(self, query, context: Context) -> Reply:
        return self.get_bot("chat").reply(query, context)

    def fetch_voice_to_text(self, voiceFile) -> Reply:
        return self.get_bot("voice_to_text").voiceToText(voiceFile)

    def fetch_text_to_voice(self, text) -> Reply:
        return self.get_bot("text_to_voice").textToVoice(text)

    def fetch_translate(self, text, from_lang="", to_lang="en") -> Reply:
        return self.get_bot("translate").translate(text, from_lang, to_lang)

    def find_chat_bot(self, bot_type: str):
        if self.chat_bots.get(bot_type) is None:
            self.chat_bots[bot_type] = create_bot(bot_type)
        return self.chat_bots.get(bot_type)

    def reset_bot(self):
        """
        重置bot路由
        """
        self.__init__()
