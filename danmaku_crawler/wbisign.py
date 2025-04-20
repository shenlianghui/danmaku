'''代码来源：https://socialsisteryi.github.io/bilibili-API-collect/docs/misc/sign/wbi.html#python'''

from functools import reduce
from hashlib import md5
import urllib.parse
import time
import requests

mixinKeyEncTab = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]

def getMixinKey(orig: str):
    '对 imgKey 和 subKey 进行字符顺序打乱编码'
    return reduce(lambda s, i: s + orig[i], mixinKeyEncTab, '')[:32]

def encWbi(params: dict, img_key: str, sub_key: str):
    '为请求参数进行 wbi 签名'
    mixin_key = getMixinKey(img_key + sub_key)
    curr_time = round(time.time())
    params['wts'] = curr_time                                  # 添加 wts 字段
    params = dict(sorted(params.items()))                      # 按照 key 重排参数
    # 过滤 value 中的 "!'()*" 字符
    params = {
        k : ''.join(filter(lambda chr: chr not in "!'()*", str(v)))
        for k, v 
        in params.items()
    }
    query = urllib.parse.urlencode(params)                     # 序列化参数
    wbi_sign = md5((query + mixin_key).encode()).hexdigest()   # 计算 w_rid
    params['w_rid'] = wbi_sign
    return params

def getWbiKeys() -> tuple[str, str]:
    '获取最新的 img_key 和 sub_key'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0',
        'Referer': 'https://www.bilibili.com/',
    }
    resp = requests.get('https://api.bilibili.com/x/web-interface/nav', headers=headers)
    resp.raise_for_status()
    json_content = resp.json()
    img_url: str = json_content['data']['wbi_img']['img_url']
    sub_url: str = json_content['data']['wbi_img']['sub_url']
    img_key = img_url.rsplit('/', 1)[1].split('.')[0]
    sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
    return img_key, sub_key

def get_danmu_wbi_sign(cid, pid, page):
    """
    生成弹幕请求的签名查询字符串
    
    参数:
        cid: 视频的cid
        pid: 视频的aid
        page: 弹幕分页页码
        
    返回:
        str: 包含签名的查询字符串
    """
    img_key, sub_key = getWbiKeys()
    base_params = {
        'type': 1,
        'oid': cid,
        'pid': pid,
        'segment_index': page,
        'web_location': 1315873
    }
    
    # 第一页特殊处理
    if page == 1:
        base_params.update({
            'pull_mode': 1,
            'ps': 0,
            'pe': 120000
        })
        
    signed_params = encWbi(
        params=base_params,
        img_key=img_key,
        sub_key=sub_key
    )
    
    query = urllib.parse.urlencode(signed_params)
    return query 