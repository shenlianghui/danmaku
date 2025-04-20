from . import danmu_pb2  # 根据 .proto 文件生成的 Python 代码
from . import wbisign
import re
import requests
import time
from django.utils import timezone
from .models import Video, Danmaku  


def extract_bvid(url):
    """
    从 Bilibili 视频 URL 中提取 BV 号。
    """
    bvid_pattern = re.compile(r'(BV[0-9a-zA-Z]+)')
    match = bvid_pattern.search(url)
    if match:
        return match.group(1)
    return None

def parse_bilibili_cookie(cookie_str):
    """
    解析B站Cookie字符串，提取关键字段
    
    参数:
        cookie_str: 从浏览器复制的完整Cookie字符串
        
    返回:
        dict: 包含解析后的关键Cookie字段
    """
    cookie_items = cookie_str.split('; ')
    
    target_cookies = {
        'SESSDATA': None,
        'bili_jct': None,
        'DedeUserID': None,
        'buvid3': None,
        'buvid_fp': None,
        '_uuid': None,
        'bili_ticket': None
    }
    
    for item in cookie_items:
        if not item:
            continue
            
        if '=' in item:
            key, value = item.split('=', 1)
            key = key.strip()
            
            if key in target_cookies:
                target_cookies[key] = value
    
    result = {k: v for k, v in target_cookies.items() if v is not None}
    
    required_fields = ['SESSDATA', 'bili_jct']
    for field in required_fields:
        if field not in result:
            raise ValueError(f"缺少必要Cookie字段: {field}")
    
    return result

def get_video_info(bvid):
    """
    通过 BV 号获取视频信息（包括CID和基本信息）。
    """
    url = f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0',
        'Referer': f'https://www.bilibili.com/video/{bvid}',
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data['code'] == 0:
            return data['data']
    return None

def get_all_cids(bvid):
    """
    通过 BV 号获取全部视频的 cid 和 duration。
    
    返回:
        list: 包含每个分P的 {'cid': cid, 'duration': duration} 字典的列表
    """
    video_info = get_video_info(bvid)
    if video_info and 'pages' in video_info:
        return [{'cid': page['cid'], 'duration': page['duration']} for page in video_info['pages']]
    return []


def get_all_danmu(cid, pid, cookie=None, max_pages=None, max_retries=3):
    """
    获取全部弹幕数据（适配新模型）
    """
    danmu_list = []
    page = 1
    while True:
        if max_pages is not None and page > max_pages:
            break

        query = wbisign.get_danmu_wbi_sign(cid, pid, page)
        url = f'https://api.bilibili.com/x/v2/dm/web/seg.so?' + query
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0',
            'Referer': 'https://www.bilibili.com/',
        }

        retries = 0
        while retries < max_retries:
            try:
                response = requests.get(url, headers=headers, cookies=cookie)
                if response.status_code == 200:
                    dm_seg_reply = danmu_pb2.DmSegMobileReply()
                    dm_seg_reply.ParseFromString(response.content)

                    if not dm_seg_reply.elems:
                        print(f'第 {page} 页没有弹幕数据，1 秒后重试...')
                        retries += 1
                        time.sleep(0.5)
                        continue

                    for danmu in dm_seg_reply.elems:
                        danmu_info = {
                            'content': danmu.text,
                            'position': danmu.stime,  # 弹幕出现时间(秒)
                            'type': danmu.mode,      # 弹幕模式
                            'font_size': danmu.size,  # 字体大小
                            'color': f'#{danmu.color:06x}',  # 颜色
                            'send_time': timezone.datetime.fromtimestamp(danmu.date),  # 发送时间
                            'is_vip': bool(danmu.weight >= 10),  # 假设权重>=10是VIP
                            'user_level_group': min(5, max(1, danmu.weight // 2))  # 将权重转换为1-5级分组
                        }
                        danmu_list.append(danmu_info)
                    print(f'已获取第 {page} 页弹幕数据')

                    page += 1
                    break
                else:
                    retries += 1
                    time.sleep(0.5)
            except Exception as e:
                print(f'解析失败: {e}，5 秒后重试...')
                retries += 1
                time.sleep(5)

        if retries >= max_retries:
            if not dm_seg_reply.elems:
                print(f'第 {page} 页弹幕数据为空，继续爬取下一页...')
                page += 1
            else:
                print(f'共获取 {page - 1} 页弹幕数据')
                break

    return danmu_list

def save_danmu_to_db(video, video_page_num, duration, danmus):
    """
    将弹幕数据保存到数据库
    """
    danmu_list = []
    for danmu in danmus:
        send_time = danmu['send_time']
        if timezone.is_naive(send_time):
            send_time = timezone.make_aware(send_time)
            
        danmu_list.append(Danmaku(
            video=video,
            video_page=video_page_num,
            duration=duration,
            content=danmu['content'],
            position=danmu['position'],
            type=danmu['type'],
            font_size=danmu['font_size'],
            color=danmu['color'],
            send_time=send_time,
            is_vip=danmu['is_vip'],
            user_level_group=danmu['user_level_group']
        ))
    
    # 批量创建提高效率
    try:
        # 批量创建 Danmaku 实例
        Danmaku.objects.bulk_create(danmu_list)
        print(f'已保存 {len(danmu_list)} 条弹幕数据到数据库')
    except Exception as e:
        # 处理批量创建失败的情况
        print(f'批量保存弹幕数据失败: {e}')
    return danmu_list[0]
