import base64
import os
import re
import tomllib
from typing import Dict, Any

import aiohttp
import requests
from loguru import logger

from WechatAPI import WechatAPIClient
from plugins.MediaParser.quanmin_parser import quan_min_factory
from utils.const import *
from utils.decorators import on_text_message, on_link_share_message
from utils.plugin_base import PluginBase


class DouyinParserError(Exception):
    """抖音解析器自定义异常基类"""
    pass


class DouyinParser(PluginBase):
    description = "抖音无水印解析插件"
    author = "姜不吃先生"  # 群友太给力了！
    version = "1.0.2"

    def __init__(self):
        super().__init__()
        self.url_pattern = {
            "抖音": {
                "pattern": re.compile(r'https?://v\.douyin\.com/\w+/?'),
                "func": self._parse_douyin
            },
            "哔哩哔哩": {
                "pattern": [
                    re.compile(r'https?://[^.]*?\.?bilibili\.com/video/\S*'),
                    re.compile(r'https?://[^.]*?\.?b23\.tv/\S*'),
                ],
                "func": [self._parse_bilibili_cyapi, self._parse_bilibili_cyapi_proxy]
            },
            "小红书": {
                "pattern": [
                    re.compile(r'https?://[^.]*?\.?xiaohongshu\.com/\S*'),
                    re.compile(r'https?://[^.]*?\.?xhslink\.com/[^\s，]*'),
                ],
                "func": self._parse_xhs_mxnzp
            },

        }

        # 读取代理配置
        config_path = os.path.join(os.path.dirname(__file__), "config.toml")
        try:
            with open(config_path, "rb") as f:
                config = tomllib.load(f)

            # 基础配置
            basic_config = config.get("basic", {})
            self.enable = basic_config.get("enable", True)
            self.http_proxy = basic_config.get("http_proxy", None)

        except Exception as e:
            logger.error(f"加载抖音解析器配置文件失败: {str(e)}")
            self.enable = True
            self.http_proxy = None

        logger.debug("[抖音] 插件初始化完成，代理设置: {}", self.http_proxy)

    async def _mxnzp_proxy(self, url, params=None, method='get', headers=None,
                           content_type='application/x-www-form-urlencoded') -> Dict[str, Any]:
        session = aiohttp.ClientSession()
        config = {
            "method": method,
            "url": url,
            "headers": headers if headers else {},
            "contentType": content_type,
            "params": params if params else {}
        }
        try:
            query = {
                'app_id': 'ompoeutptkuotnet',
                'app_secret': '7F80NooCtCeUCBKa0yN1w3VdKGKYNk70',
                'config': base64.b64encode(str(config).encode("utf-8")).decode("utf-8")
            }
            api = 'https://www.mxnzp.com/api/request_proxy/request?' + '&'.join([f'{k}={v}' for k, v in query.items()])
            async with session.get(api, timeout=10) as resp:
                info = await resp.json()
            if info.get('code', '0') != 1:
                raise DouyinParserError("mxnzp proxy 请求失败")
            info = info.get('data', {}).get('result')
        except Exception as e:
            logger.error(f"mxnzp解析bilibili视频失败：{e}")
            raise DouyinParserError(e)
        finally:
            await session.close()
        return info

    async def _parse_bilibili_mxnzp(self, url: str) -> Dict[str, Any]:
        """这个api已经收费了"""
        data = {}
        session = aiohttp.ClientSession()
        try:
            query = {
                'app_id': 'ompoeutptkuotnet',
                'app_secret': '7F80NooCtCeUCBKa0yN1w3VdKGKYNk70',
                'url': base64.b64encode(url.encode("utf-8")).decode("utf-8")
            }
            api = 'https://www.mxnzp.com/api/bilibili/video?' + '&'.join([f'{k}={v}' for k, v in query.items()])
            async with session.get(api, timeout=10) as resp:
                info = await resp.json()
            if info.get('code', '0') != 1 or not info.get('data', {}).get('list', []):
                raise DouyinParserError(f"mxnzp 解析bilibili视频失败:{info}")
            info = info.get('data')
            data["title"] = info.get("title", '')
            data["name"] = info.get("author", '')
            data["cover"] = info.get("cover", '')
            data["video"] = info.get("list")[0].get('url')
        except Exception as e:
            logger.error(f"mxnzp解析bilibili视频失败：{e}")
            raise DouyinParserError(e)
        finally:
            await session.close()
        return data

    async def _parse_xhs_mxnzp(self, url: str) -> Dict[str, Any]:
        data = {}
        session = aiohttp.ClientSession()
        try:
            query = {
                'app_id': 'ompoeutptkuotnet',
                'app_secret': '7F80NooCtCeUCBKa0yN1w3VdKGKYNk70',
                'url': base64.b64encode(url.encode("utf-8")).decode("utf-8")
            }
            api = 'https://www.mxnzp.com/api/xhs/video?' + '&'.join([f'{k}={v}' for k, v in query.items()])
            async with session.get(api, timeout=10) as resp:
                info = await resp.json()
            if info.get('code', '0') != 1 or not info.get('data', {}):
                raise DouyinParserError(f"mxnzp 解析小红书链接失败:{info}")
            info = info.get('data')
            if not info.get('url', ''):
                raise DouyinParserError(f"当前小红书链接没有视频~")
            data["cover"] = info.get("cover", '')
            data["title"] = info.get("title", '') if info.get('title', '') else info.get('desc', '')
            data["name"] = info.get("author", '')
            data["video"] = info.get("url")
        except Exception as e:
            logger.error(f"mxnzp解析小红书视频失败：{e}")
            raise DouyinParserError(e)
        finally:
            await session.close()
        return data

    async def _parse_bilibili_cyapi_proxy(self, url: str) -> Dict[str, Any]:
        """cyapi接口不稳定，使用_mxnzp_proxy代理请求"""
        data = {}
        session = aiohttp.ClientSession()
        try:
            info = await self._mxnzp_proxy('https://apih.kfcgw50.me/api/bilibili-info?url=' + url)
            data["title"] = info.get("title", '')
            data["name"] = info.get("author", '')
            data["cover"] = info.get("cover", '')
        except BaseException as e:
            logger.warning(f"cyapi bilibili-info: {e}")

        try:
            json = await self._mxnzp_proxy('https://apih.kfcgw50.me/api/bilibili-video-parse2?url=' + url)
            if not json.get('code') == 0:
                raise DouyinParserError(f"cyapi 请求bilibili视频失败: {json}")
            data["video"] = json.get("url")
        except Exception as e:
            logger.warning(f"cyapi 解析bilibili视频失败：{e}")
            raise DouyinParserError(e)
        finally:
            await session.close()
        return data

    async def _parse_bilibili_cyapi(self, url: str) -> Dict[str, Any]:
        """这个接口不稳定，考虑使用_parse_bilibili_cyapi_proxy"""
        data = {}
        session = aiohttp.ClientSession()
        try:
            api = 'https://apih.kfcgw50.me/api/bilibili-video'
            async with session.get(api, params={'url': url}, timeout=10) as resp:
                info = await resp.json()
            data["title"] = info.get("title", '')
            data["name"] = info.get("author", '')
            data["cover"] = info.get("cover", '')
        except BaseException as e:
            logger.warning(f"cyapi bilibili-info: {e}")

        try:
            api = 'https://apih.kfcgw50.me/api/bilibili-video-parse2'
            async with session.get(api, params={'url': url}, timeout=10) as resp:
                json = await resp.json()
            if not json.get('code') == 0:
                raise DouyinParserError(f"cyapi 请求bilibili视频失败: {json}")
            data["video"] = json.get("url")
        except Exception as e:
            logger.warning(f"cyapi 解析bilibili视频失败：{e}")
            raise DouyinParserError(e)
        finally:
            await session.close()
        return data

    async def _parse_douyin(self, url: str) -> Dict[str, Any]:
        try:
            url = self._clean_url(url)
            json = requests.get("http://www.yx520.ltd/API/dyjx/api.php?url=" + url).json()
        except Exception as e:
            logger.error(f"解析抖音视频失败{e}")
            raise DouyinParserError("解析抖音视频失败")

        json["video"] = json["media_url"]
        json["title"] = json["song_name"]
        json["name"] = json["artist_name"]
        json["cover"] = json["img_url"]
        return json

    def _clean_url(self, url: str) -> str:
        """清理URL中的特殊字符"""
        cleaned_url = url.strip().replace(';', '').replace('\n', '').replace('\r', '')
        logger.debug("[抖音] 清理后的URL: {}", cleaned_url)  # 添加日志
        return cleaned_url

    @on_text_message(priority=80)
    async def handle_media_links(self, bot: WechatAPIClient, message: dict):
        content = message['Content']
        sender = message['SenderWxid']
        chat_id = message['FromWxid']

        try:
            platform, match, func = '', None, None
            for name, rule in self.url_pattern.items():
                p = rule['pattern'] if isinstance(rule['pattern'], list) else [rule['pattern']]
                if match:
                    break

                for pattern in p:
                    match = pattern.search(content)
                    if match:
                        platform, func = name, rule['func']
                        break

            # 尝试匹配 全民解析
            if not match:
                parser = quan_min_factory.createParser(content)
                if parser:
                    http_re = re.compile(r'https?://[^\s/?#]+\S*')
                    platform, match, func = str(parser), http_re.search(content), parser.handle

            if not match:
                return PLUGIN_PASS
            # 解析视频信息
            video_info = {}

            original_url = match.group(0)
            logger.info(f"发现{platform}链接: {original_url}")

            # 添加解析提示
            msg_args = {
                'wxid': chat_id,
                'content': f"检测到{platform}分享链接，尝试解析视频...",
                'at': [sender] if message['IsGroup'] else []
            }
            await bot.send_text_message(**msg_args)

            if not isinstance(func, list):
                func = [func]
            for fun in func:
                try:
                    video_info = await fun(original_url)
                    if video_info:
                        break
                except Exception as e:
                    logger.warning(
                        f"解析视频信息异常:{e}, {e.__traceback__.tb_frame.f_code.co_filename}:{e.__traceback__.tb_lineno}")

            if not video_info:
                raise DouyinParserError("无法获取视频信息")

            # 获取视频信息
            video_url = video_info.get('video', '')
            title = video_info.get('title', '无标题')
            author = video_info.get('name', '未知作者')
            cover = video_info.get('cover', '')

            if not video_url:
                raise DouyinParserError("无法获取视频地址")

            # 发送卡片版消息
            await bot.send_link_message(
                wxid=chat_id,
                url=video_url,
                title=f"{title[:30]} - {author[:10]}" if author else title[:40],
                description="使用浏览器打开可下载保存",
                thumb_url=cover
            )

            logger.info(f"已发送解析结果: 标题[{title}] 作者[{author}]")

        except DouyinParserError as e:
            error_msg = str(e) if str(e) else "解析失败"
            logger.error(f"抖音解析失败: {error_msg}")
            if message['IsGroup']:
                await bot.send_text_message(wxid=chat_id, content=f"视频解析失败: {error_msg}\n", at=[sender])
            else:
                await bot.send_text_message(wxid=chat_id, content=f"视频解析失败: {error_msg}")
        except Exception as e:
            error_msg = str(e) if str(e) else "未知错误"
            logger.error(f"抖音解析发生未知错误: {error_msg}")
            if message['IsGroup']:
                await bot.send_text_message(wxid=chat_id, content=f"视频解析失败: {error_msg}\n", at=[sender])
            else:
                await bot.send_text_message(wxid=chat_id, content=f"视频解析失败: {error_msg}")
        return PLUGIN_ENDED

    @on_link_share_message
    async def handle_share_media_links(self, bot: WechatAPIClient, message: dict):
        if not message.get('url', ''):
            return PLUGIN_PASS
        message['Content'] = message.get('url', '')

        return await self.handle_media_links(bot, message)

    async def async_init(self):
        """异步初始化函数"""
        # 可以在这里进行一些异步的初始化操作
        # 比如测试API可用性等
        pass
