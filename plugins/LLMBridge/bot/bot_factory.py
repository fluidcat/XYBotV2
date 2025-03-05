"""
channel factory
"""
from plugins.LLMBridge.common import const


def create_bot(bot_type):
    """
    create a bot_type instance
    :param bot_type: bot type code
    :return: bot instance
    """
    if bot_type == const.BAIDU:
        # 替换Baidu Unit为Baidu文心千帆对话接口
        # from bot.baidu.baidu_unit_bot import BaiduUnitBot
        # return BaiduUnitBot()
        from plugins.LLMBridge.bot.baidu.baidu_wenxin import BaiduWenxinBot
        return BaiduWenxinBot()

    elif bot_type == const.CHATGPT:
        # ChatGPT 网页端web接口
        from plugins.LLMBridge.bot.chatgpt.chat_gpt_bot import ChatGPTBot
        return ChatGPTBot()

    elif bot_type == const.OPEN_AI:
        # OpenAI 官方对话模型API
        from plugins.LLMBridge.bot.openai.open_ai_bot import OpenAIBot
        return OpenAIBot()

    elif bot_type == const.CHATGPTONAZURE:
        # Azure chatgpt service https://azure.microsoft.com/en-in/products/cognitive-services/openai-service/
        from plugins.LLMBridge.bot.chatgpt.chat_gpt_bot import AzureChatGPTBot
        return AzureChatGPTBot()

    elif bot_type == const.XUNFEI:
        from plugins.LLMBridge.bot.xunfei.xunfei_spark_bot import XunFeiBot
        return XunFeiBot()

    elif bot_type == const.LINKAI:
        from plugins.LLMBridge.bot.linkai.link_ai_bot import LinkAIBot
        return LinkAIBot()

    elif bot_type == const.CLAUDEAI:
        from plugins.LLMBridge.bot.claude.claude_ai_bot import ClaudeAIBot
        return ClaudeAIBot()
    elif bot_type == const.CLAUDEAPI:
        from plugins.LLMBridge.bot.claudeapi.claude_api_bot import ClaudeAPIBot
        return ClaudeAPIBot()
    elif bot_type == const.QWEN:
        from plugins.LLMBridge.bot.ali.ali_qwen_bot import AliQwenBot
        return AliQwenBot()
    elif bot_type == const.QWEN_DASHSCOPE:
        from plugins.LLMBridge.bot.dashscope.dashscope_bot import DashscopeBot
        return DashscopeBot()
    elif bot_type == const.GEMINI:
        from plugins.LLMBridge.bot.gemini.google_gemini_bot import GoogleGeminiBot
        return GoogleGeminiBot()

    elif bot_type == const.ZHIPU_AI:
        from plugins.LLMBridge.bot.zhipuai.zhipuai_bot import ZHIPUAIBot
        return ZHIPUAIBot()

    elif bot_type == const.MOONSHOT:
        from plugins.LLMBridge.bot.moonshot.moonshot_bot import MoonshotBot
        return MoonshotBot()
    
    elif bot_type == const.MiniMax:
        from plugins.LLMBridge.bot.minimax.minimax_bot import MinimaxBot
        return MinimaxBot()


    raise RuntimeError
