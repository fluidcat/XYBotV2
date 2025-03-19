import hashlib
import time
from urllib.parse import urlparse

import requests
from loguru import logger


class QuanMinParser:

    def __init__(self):
        self.parsers = {}
        self.site_dict = {
            "163": {"name": "网易云音乐", "site": "yinyue", "salt": "2HT8gjE3xL"},
            "miaopai": {"name": "秒拍", "site": "weibo", "salt": "2HT8gjE3xL"},
            "xiaokaxiu": {"name": "小咖秀", "site": "weibo", "salt": "2HT8gjE3xL"},
            "yixia": {"name": "yixia", "site": "weibo", "salt": "2HT8gjE3xL"},
            "weibo": {"name": "微博", "site": "weibo", "salt": "2HT8gjE3xL"},
            "weico": {"name": "微博", "site": "weibo", "salt": "2HT8gjE3xL"},
            "meipai": {"name": "美拍", "site": "meipai", "salt": "2HT8gjE3xL"},
            "xiaoying": {"name": "xiaoying", "site": "xiaoying", "salt": "2HT8gjE3xL"},
            "vivavideo": {"name": "xiaoying", "site": "xiaoying", "salt": "2HT8gjE3xL"},
            "immomo": {"name": "陌陌", "site": "momo", "salt": "2HT8gjE3xL"},
            "momocdn": {"name": "陌陌", "site": "momo", "salt": "2HT8gjE3xL"},
            "inke": {"name": "映客", "site": "inke", "salt": "2HT8gjE3xL"},
            "weishi.qq": {"name": "微视", "site": "weishi", "salt": "2HT8gjE3xL"},
            "qzone.qq": {"name": "微视", "site": "weishi", "salt": "2HT8gjE3xL"},
            "kg4.qq": {"name": "全民K歌", "site": "kg", "salt": "2HT8gjE3xL"},
            "kg3.qq": {"name": "全民K歌", "site": "kg", "salt": "2HT8gjE3xL"},
            "kg2.qq": {"name": "全民K歌", "site": "kg", "salt": "2HT8gjE3xL"},
            "kg1.qq": {"name": "全民K歌", "site": "kg", "salt": "2HT8gjE3xL"},
            "kg.qq": {"name": "全民K歌", "site": "kg", "salt": "2HT8gjE3xL"},
            "facebook": {"name": "脸书", "site": "facebook", "salt": "2HT8gjE3xL"},
            "fb": {"name": "脸书", "site": "facebook", "salt": "2HT8gjE3xL"},
            "youtube": {"name": "YouTube", "site": "youtube", "salt": "2HT8gjE3xL"},
            "youtu": {"name": "YouTube", "site": "youtube", "salt": "2HT8gjE3xL"},
            "vimeo": {"name": "vimeo", "site": "vimeo", "salt": "2HT8gjE3xL"},
            "twitter": {"name": "twitter", "site": "twitter", "salt": "2HT8gjE3xL"},
            "instagram": {"name": "instagram", "site": "instagram", "salt": "2HT8gjE3xL"},
            "hao222": {"name": "hao222", "site": "quanmin", "salt": "2HT8gjE3xL"},
            "haokan.baidu": {"name": "好看视频", "site": "quanmin", "salt": "2HT8gjE3xL"},
            "pearvideo": {"name": "梨视频", "site": "pearvideo", "salt": "2HT8gjE3xL"},
            "tumblr": {"name": "汤不热", "site": "tumblr", "salt": "2HT8gjE3xL"},
            "luisonte": {"name": "luisonte", "site": "tumblr", "salt": "2HT8gjE3xL"},
            "izuiyou": {"name": "最右", "site": "zuiyou", "salt": "2HT8gjE3xL"},

            "bilibili": {"name": "哔哩哔哩", "site": "bilibili", "salt": "6HTugjCXxR", "root": "snapany.com"},
            "b23": {"name": "哔哩哔哩", "site": "bilibili", "salt": "6HTugjCXxR", "root": "snapany.com"},
            "threads": {"name": "threads", "site": "threads", "salt": "6HTugjCXxR", "root": "snapany.com"},
            "pinterest": {"name": "pinterest", "site": "pinterest", "salt": "6HTugjCXxR", "root": "snapany.com"},
            "pin": {"name": "pinterest", "site": "pinterest", "salt": "6HTugjCXxR", "root": "snapany.com"},
            "tiktok": {"name": "抖音", "site": "tiktok", "salt": "6HTugjCXxR", "root": "snapany.com"},
            "tiktokv": {"name": "抖音", "site": "tiktok", "salt": "6HTugjCXxR", "root": "snapany.com"},
            "tiktokcdn": {"name": "抖音", "site": "tiktok", "salt": "6HTugjCXxR", "root": "snapany.com"},
            "musical": {"name": "musical.ly", "site": "tiktok", "salt": "6HTugjCXxR", "root": "snapany.com"},
            "musemuse": {"name": "musemuse", "site": "tiktok", "salt": "6HTugjCXxR", "root": "snapany.com"},
            "muscdn": {"name": "musemuse", "site": "tiktok", "salt": "6HTugjCXxR", "root": "snapany.com"},
            "vigovideo": {"name": "火山小视频", "site": "tiktok", "salt": "6HTugjCXxR", "root": "snapany.com"},
            "douyin": {"name": "抖音", "site": "tiktok", "salt": "6HTugjCXxR", "root": "snapany.com"},
            "snapchat": {"name": "snapchat", "site": "snapchat", "salt": "6HTugjCXxR", "root": "snapany.com"},
            "vk": {"name": "vk", "site": "vk", "salt": "6HTugjCXxR", "root": "snapany.com"},
            "suno": {"name": "suno", "site": "suno", "salt": "6HTugjCXxR", "root": "snapany.com"},
        }

    def createParser(self, url):
        d1, d2 = self.extract_domain(url)
        parser = self.parsers.get(d1, self.parsers.get(d2))
        if parser:
            return parser

        site = self.site_dict.get(d1, self.site_dict.get(d2))
        if not site:
            return

        if site.get('root') == "snapany.com":
            parser = SnapanyParser(**site)
        else:
            parser = IiilabParser(**site)
        self.parsers[d1] = parser
        self.parsers[d2] = parser
        return parser

    def extract_domain(self, url: str):
        """返回去除后缀的二级域名"""
        ds = ['', '']
        if not url:
            return ds
        try:
            hostname = urlparse(url).hostname
            if not hostname:
                return ds
            parts = hostname.split(".")
            level1 = parts[-2].lower() if len(parts) >= 2 else ""
            level2 = f"{parts[-3]}.{parts[-2]}".lower() if len(parts) > 2 else ""
            return level2, level1
        except Exception:
            return ds


quan_min_factory = QuanMinParser()


class ParserBase:

    def __init__(self):
        self.name = "default"

    def handle(self, url) -> dict:
        return {}

    def __str__(self):
        return self.name


class IiilabParser(ParserBase):

    def __init__(self, name, site, salt):
        super().__init__()
        self.name = name
        self.site = site
        self.salt = salt
        self.root = 'iiilab.com'
        self.api = f'https://{site}.{self.root}/api/extract'

    async def handle(self, url):
        result = {}
        json = {
            'site': self.site,
            'link': url
        }
        resp = requests.post(self.api, json=json, headers=self.getHeaders(url), timeout=20)
        logger.warning(f"{self.site} 解析 {url}，{resp.text}")
        if not resp or not resp.json().get('medias', []):
            logger.warning(f"{self.site} 解析 {url} 失败，{resp.text}")
            return result
        resp = resp.json()
        result["title"] = resp.get('text')
        if resp.get('medias')[0].get("media_type") == 'audio':
            result["audio"] = resp.get('medias')[0].get("resource_url")
        if resp.get('medias')[0].get("media_type") == 'video':
            result["video"] = resp.get('medias')[0].get("resource_url")

        return result

    def getHeaders(self, url):
        ts = str(int(time.time() * 1000))
        # 'url + site + Timestamp + salt'
        md5 = hashlib.md5(f"{url}{self.site}{ts}{self.salt}".encode("utf-8")).hexdigest()
        return {
            "G-Timestamp": ts,
            "G-Footer": md5,
            "Content-Type": "application/json",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/122.0.6261.95 Safari/537.36",
            "authority": f"{self.site}.{self.root}",
            "origin": f"https://{self.site}.{self.root}",
            "referer": f"https://{self.site}.{self.root}/"
        }


class SnapanyParser(ParserBase):

    def __init__(self, name, site, salt):
        super().__init__()
        self.name = name
        self.path = site
        self.salt = salt
        self.root = 'snapany.com'
        self.locale = 'zh'
        self.api = f'https://{self.root}/api/extract'

    async def handle(self, url):
        result = {}
        json = {'link': url}
        resp = requests.post(self.api, json=json, headers=self.getHeaders(url), timeout=20)
        if not resp or not resp.json().get('medias', []):
            logger.warning(f"{self.path} 解析 {url} 失败，{resp}")
            return result
        resp = resp.json()
        result["title"] = resp.get('text')
        if resp.get('medias')[0].get("media_type") == 'audio':
            result["audio"] = resp.get('medias')[0].get("resource_url")
        if resp.get('medias')[0].get("media_type") == 'video':
            result["video"] = resp.get('medias')[0].get("resource_url")
            result["cover"] = resp.get('medias')[0].get("preview_url")

        return result

    def getHeaders(self, url):
        ts = str(int(time.time() * 1000))
        # 'url + site + Timestamp + salt'
        md5 = hashlib.md5(f"{url}{self.locale}{ts}{self.salt}".encode("utf-8")).hexdigest()
        return {
            "Accept-Language": self.locale,
            "G-Timestamp": ts,
            "G-Footer": md5,
            "Content-Type": "application/json",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/122.0.6261.95 Safari/537.36",
            "authority": f"{self.root}",
            "origin": f"https://{self.root}",
            "referer": f"https://{self.root}/{self.locale}/{self.path}"
        }
