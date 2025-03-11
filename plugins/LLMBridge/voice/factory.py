"""
voice factory
"""


def create_voice(voice_type):
    """
    create a voice instance
    :param voice_type: voice type code
    :return: voice instance
    """
    if voice_type == "baidu":
        from plugins.LLMBridge.voice.baidu.baidu_voice import BaiduVoice
        return BaiduVoice()
    elif voice_type == "google":
        from plugins.LLMBridge.voice.google.google_voice import GoogleVoice

        return GoogleVoice()
    elif voice_type == "openai":
        from plugins.LLMBridge.voice.openai.openai_voice import OpenaiVoice

        return OpenaiVoice()
    elif voice_type == "pytts":
        from plugins.LLMBridge.voice.pytts.pytts_voice import PyttsVoice

        return PyttsVoice()
    elif voice_type == "azure":
        from plugins.LLMBridge.voice.azure.azure_voice import AzureVoice

        return AzureVoice()
    elif voice_type == "elevenlabs":
        from plugins.LLMBridge.voice.elevent.elevent_voice import ElevenLabsVoice

        return ElevenLabsVoice()

    elif voice_type == "linkai":
        from plugins.LLMBridge.voice.linkai.linkai_voice import LinkAIVoice

        return LinkAIVoice()
    elif voice_type == "ali":
        from plugins.LLMBridge.voice.ali.ali_voice import AliVoice

        return AliVoice()
    elif voice_type == "edge":
        from plugins.LLMBridge.voice.edge.edge_voice import EdgeVoice

        return EdgeVoice()
    elif voice_type == "xunfei":
        from plugins.LLMBridge.voice.xunfei.xunfei_voice import XunfeiVoice

        return XunfeiVoice()
    elif voice_type == "tencent":
        from plugins.LLMBridge.voice.tencent.tencent_voice import TencentVoice

        return TencentVoice()
    raise RuntimeError
