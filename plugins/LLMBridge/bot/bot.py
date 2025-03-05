"""
Auto-replay chat robot abstract class
"""


from plugins.LLMBridge.bridge.context import Context
from plugins.LLMBridge.bridge.reply import Reply


class Bot(object):
    def reply(self, query, context: Context = None) -> Reply:
        """
        bot auto-reply content
        :param req: received message
        :return: reply content
        """
        raise NotImplementedError
