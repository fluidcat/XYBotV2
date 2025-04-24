from .acfun import AcFun
from .base import VideoInfo, VideoSource
from .doupai import DouPai
from .douyin import DouYin
from .haokan import HaoKan
from .huya import HuYa
from .kuaishou import KuaiShou
from .lishipin import LiShiPin
from .lvzhou import LvZhou
from .meipai import MeiPai
from .pipigaoxiao import PiPiGaoXiao
from .pipixia import PiPiXia
from .quanmin import QuanMin
from .quanminkge import QuanMinKGe
from .redbook import RedBook
from .sixroom import SixRoom
from .weibo import WeiBo
from .weishi import WeiShi
from .xigua import XiGua
from .xinpianchang import XinPianChang
from .zuiyou import ZuiYou

# 视频来源与解析器的映射关系
video_source_info_mapping = {
    VideoSource.AcFun: {
        "domain_list": ["www.acfun.cn"],
        "parser": AcFun,
    },
    VideoSource.DouPai: {
        "domain_list": ["doupai.cc"],
        "parser": DouPai,
    },
    VideoSource.DouYin: {
        "domain_list": ["v.douyin.com", "www.iesdouyin.com", "www.douyin.com"],
        "parser": DouYin,
    },
    VideoSource.HaoKan: {
        "domain_list": [
            "haokan.baidu.com",
            "haokan.hao123.com",
        ],
        "parser": HaoKan,
    },
    VideoSource.HuYa: {
        "domain_list": ["v.huya.com"],
        "parser": HuYa,
    },
    VideoSource.KuaiShou: {
        "domain_list": ["v.kuaishou.com"],
        "parser": KuaiShou,
    },
    VideoSource.LiShiPin: {
        "domain_list": ["www.pearvideo.com"],
        "parser": LiShiPin,
    },
    VideoSource.LvZhou: {
        "domain_list": ["weibo.cn"],
        "parser": LvZhou,
    },
    VideoSource.MeiPai: {
        "domain_list": ["meipai.com"],
        "parser": MeiPai,
    },
    VideoSource.PiPiGaoXiao: {
        "domain_list": ["h5.pipigx.com"],
        "parser": PiPiGaoXiao,
    },
    VideoSource.PiPiXia: {
        "domain_list": ["h5.pipix.com"],
        "parser": PiPiXia,
    },
    VideoSource.QuanMin: {
        "domain_list": ["xspshare.baidu.com"],
        "parser": QuanMin,
    },
    VideoSource.QuanMinKGe: {
        "domain_list": ["kg.qq.com"],
        "parser": QuanMinKGe,
    },
    VideoSource.SixRoom: {
        "domain_list": ["6.cn"],
        "parser": SixRoom,
    },
    VideoSource.WeiBo: {
        "domain_list": ["weibo.com"],
        "parser": WeiBo,
    },
    VideoSource.WeiShi: {
        "domain_list": ["isee.weishi.qq.com"],
        "parser": WeiShi,
    },
    VideoSource.XiGua: {
        "domain_list": ["v.ixigua.com", "www.ixigua.com"],
        "parser": XiGua,
    },
    VideoSource.XinPianChang: {
        "domain_list": ["xinpianchang.com"],
        "parser": XinPianChang,
    },
    VideoSource.ZuiYou: {
        "domain_list": ["share.xiaochuankeji.cn"],
        "parser": ZuiYou,
    },
    VideoSource.RedBook: {
        "domain_list": [
            "www.xiaohongshu.com",
            "xhslink.com",
        ],
        "parser": RedBook,
    },
}

name_dict = {
    VideoSource.DouYin: "抖音/抖音火山版",
    VideoSource.KuaiShou: "快手",
    VideoSource.PiPiXia: "皮皮虾",
    VideoSource.WeiBo: "微博",
    VideoSource.WeiShi: "微视",
    VideoSource.LvZhou: "绿洲",
    VideoSource.ZuiYou: "最右",
    VideoSource.QuanMin: "度小视(全民小视频)",
    VideoSource.XiGua: "西瓜",
    VideoSource.LiShiPin: "梨视频",
    VideoSource.PiPiGaoXiao: "皮皮搞笑",
    VideoSource.HuYa: "虎牙",
    VideoSource.AcFun: "A站",
    VideoSource.DouPai: "逗拍",
    VideoSource.MeiPai: "美拍",
    VideoSource.QuanMinKGe: "全民K歌",
    VideoSource.SixRoom: "六间房",
    VideoSource.XinPianChang: "新片场",
    VideoSource.HaoKan: "好看视频",
    VideoSource.RedBook: "小红书",
}


async def parse_video_share_url(share_url: str) -> VideoInfo:
    """
    解析分享链接, 获取视频信息
    :param share_url: 视频分享链接
    :return:
    """
    source = ""
    for item_source, item_source_info in video_source_info_mapping.items():
        for item_url_domain in item_source_info["domain_list"]:
            if item_url_domain in share_url:
                source = item_source
                break
        if source:
            break

    if not source:
        raise ValueError(f"share url [{share_url}] does not have source config")

    url_parser = video_source_info_mapping[source]["parser"]
    if not url_parser:
        raise ValueError(f"source {source} has no video parser")

    _obj = url_parser()
    video_info = await _obj.parse_share_url(share_url)

    return video_info


def can_parse_video_share_url(share_url: str) -> str:
    source = ""
    for item_source, item_source_info in video_source_info_mapping.items():
        for item_url_domain in item_source_info["domain_list"]:
            if item_url_domain in share_url:
                source = item_source
                break
        if source:
            break

    if not source:
        return

    return name_dict[source]


async def parse_video_id(source: VideoSource, video_id: str) -> VideoInfo:
    """
    解析视频ID, 获取视频信息
    :param source: 视频来源
    :param video_id: 视频id
    :return:
    """
    if not video_id or not source:
        raise ValueError("video_id or source is empty")

    id_parser = video_source_info_mapping[source]["parser"]
    if not id_parser:
        raise ValueError(f"source {source} has no video parser")

    _obj = id_parser()
    video_info = await _obj.parse_video_id(video_id)

    return video_info
