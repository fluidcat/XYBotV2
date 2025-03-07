from cachetools import TTLCache
import datetime
from inspect import iscoroutinefunction
import functools


class MyDailyCache:
    def __init__(self, maxsize=128):
        """
        初始化 DailyCache。
        :param maxsize: 缓存的最大容量。
        """
        self.maxsize = maxsize
        self.cache = self._create_cache()

    def _get_seconds_until_midnight(self):
        """
        计算当前时间到次日凌晨 12 点的时间差（秒）。
        :return: 到次日凌晨 12 点的秒数。
        """
        now = datetime.datetime.now()
        midnight = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return (midnight - now).total_seconds()

    def _create_cache(self):
        """
        创建一个新的 TTLCache，设置 ttl 为到次日凌晨 12 点的时间差。
        :return: TTLCache 实例。
        """
        ttl = self._get_seconds_until_midnight()
        return TTLCache(maxsize=self.maxsize, ttl=ttl)

    def get(self, key, default=None):
        """
        从缓存中获取值。
        :param key: 缓存键。
        :param default: 如果键不存在，返回的默认值。
        :return: 缓存值或默认值。
        """
        return self.cache.get(key, default)

    def set(self, key, value):
        """
        将值存入缓存。
        :param key: 缓存键。
        :param value: 缓存值。
        """
        self.cache[key] = value

    def clear(self):
        """
        清空缓存。
        """
        self.cache.clear()

    def __contains__(self, key):
        """
        检查缓存中是否包含指定键。
        :param key: 缓存键。
        :return: 如果键存在，返回 True；否则返回 False。
        """
        return key in self.cache

    def __getitem__(self, key):
        """
        获取缓存值。
        :param key: 缓存键。
        :return: 缓存值。
        """
        return self.cache[key]

    def __setitem__(self, key, value):
        """
        设置缓存值。
        :param key: 缓存键。
        :param value: 缓存值。
        """
        self.cache[key] = value

    def __delitem__(self, key):
        """
        删除缓存项。
        :param key: 缓存键。
        """
        del self.cache[key]

    def __len__(self):
        """
        获取缓存中的项数。
        :return: 缓存中的项数。
        """
        return len(self.cache)

    def __repr__(self):
        """
        返回缓存的字符串表示。
        :return: 缓存的字符串表示。
        """
        return repr(self.cache)


# 创建全局 DailyCache 实例
daily_cache_instance = MyDailyCache()


def daily_cache(func):
    """
    缓存装饰器，支持同步和异步函数，将函数的返回值缓存到 DailyCache 中。
    :param func: 被装饰的函数。
    :return: 装饰后的函数。
    """

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        # 生成缓存键
        cache_key = (func.__name__, args, frozenset(kwargs.items()))
        # 如果缓存中存在，直接返回缓存值
        if cache_key in daily_cache_instance:
            return daily_cache_instance[cache_key]
        # 否则调用函数，并将结果存入缓存
        result = func(*args, **kwargs)
        daily_cache_instance[cache_key] = result
        return result

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        # 生成缓存键
        cache_key = (func.__name__, args, frozenset(kwargs.items()))
        # 如果缓存中存在，直接返回缓存值
        if cache_key in daily_cache_instance:
            return daily_cache_instance[cache_key]
        # 否则调用异步函数，并将结果存入缓存
        result = await func(*args, **kwargs)
        daily_cache_instance[cache_key] = result
        return result

    # 根据函数类型返回对应的包装器
    if iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper
