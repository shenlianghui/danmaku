import re
import time
import json
import logging
import requests
from datetime import datetime
from django.utils import timezone
from django.db import transaction
from django.conf import settings

from .models import Video, Danmaku, CrawlTask
from . import danmu_pb2
from . import wbisign

logger = logging.getLogger(__name__)

class BilibiliDanmakuCrawler:
    """B站弹幕爬虫类"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0',
            'Referer': 'https://www.bilibili.com',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def parse_bvid(self, url):
        """从URL中提取BV号"""
        bv_pattern = r'BV\w{10}'
        match = re.search(bv_pattern, url)
        if match:
            return match.group(0)
        return None
    
    def parse_bilibili_cookie(self, cookie_str):
        """
        解析B站Cookie字符串，提取关键字段
        
        参数:
            cookie_str: 从浏览器复制的完整Cookie字符串
            
        返回:
            dict: 包含解析后的关键Cookie字段
        """
        if not cookie_str:
            return {}
            
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
        
        return {k: v for k, v in target_cookies.items() if v is not None}
    
    def get_video_info(self, bvid):
        """获取视频信息"""
        api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        try:
            response = self.session.get(api_url)
            if response.status_code == 200:
                data = response.json()
                if data['code'] == 0:
                    info = data['data']
                    return info
                else:
                    logger.error(f"获取视频信息失败: {data['message']}")
            else:
                logger.error(f"API请求失败: {response.status_code}")
        except Exception as e:
            logger.error(f"获取视频信息异常: {str(e)}")
        return None
    
    def get_all_cids(self, bvid):
        """
        通过 BV 号获取全部视频的 cid 和 duration。
        
        返回:
            list: 包含每个分P的 {'cid': cid, 'duration': duration} 字典的列表
        """
        video_info = self.get_video_info(bvid)
        try:
            if video_info and 'pages' in video_info:
                return [{'cid': page['cid'], 'duration': page['duration']} for page in video_info['pages']]
            else:
                logger.error(f"获取分P信息失败!")
        except Exception as e:
            logger.error(f"获取分P信息异常: {str(e)}")
        
        return []
    
    def get_danmaku_pb(self, cid, pid, page=1, cookie=None, max_retries=3):
        """
        获取弹幕数据(protobuf格式)
        
        参数:
            cid: 视频的cid
            pid: 视频的aid
            page: 弹幕分页页码
            cookie: Cookie字典
            max_retries: 最大重试次数
            
        返回:
            list: 弹幕数据列表
        """
        query = wbisign.get_danmu_wbi_sign(cid, pid, page)
        api_url = f'https://api.bilibili.com/x/v2/dm/web/seg.so?{query}'
        
        for retry in range(max_retries):
            try:
                response = self.session.get(api_url, cookies=cookie)
                if response.status_code == 200:
                    dm_seg_reply = danmu_pb2.DmSegMobileReply()
                    dm_seg_reply.ParseFromString(response.content)
                    
                    if not dm_seg_reply.elems:
                        logger.info(f"第 {page} 页没有弹幕数据")
                        if retry < max_retries - 1:
                            time.sleep(1)
                            continue
                        return []
                    
                    return dm_seg_reply.elems
            except Exception as e:
                logger.error(f"解析弹幕数据异常: {str(e)}")
                if retry < max_retries - 1:
                    time.sleep(2)
        
        return []
    
    def get_all_danmaku(self, cid, pid, cookie=None, max_pages=None):
        """
        获取全部弹幕数据
        
        参数:
            cid: 视频的cid
            pid: 视频的aid
            cookie: Cookie字典
            max_pages: 最大页数限制
            
        返回:
            list: 所有弹幕数据列表
        """
        all_danmakus = []
        page = 1
        
        while True:
            if max_pages and page > max_pages:
                break
                
            danmakus = self.get_danmaku_pb(cid, pid, page, cookie)
            if not danmakus:
                # 没有更多弹幕数据，结束循环
                break
                
            logger.info(f"获取到第 {page} 页弹幕数据: {len(danmakus)} 条")
            all_danmakus.extend(danmakus)
            
            # 防止请求过快
            time.sleep(1)
            page += 1
        
        return all_danmakus
    
    def parse_danmaku(self, danmakus, video_obj, page_num=1, page_duration=0):
        """
        解析弹幕数据并保存到数据库
        
        参数:
            danmakus: protobuf格式的弹幕数据
            video_obj: 视频对象
            page_num: 分P编号
            page_duration: 分P时长
            
        返回:
            int: 保存的弹幕数量
        """
        danmaku_list = []
        count = 0
        
        try:
            with transaction.atomic():
                for d in danmakus:
                    # 不再检查弹幕是否存在，因为旧数据已被删除
                    # if Danmaku.objects.filter(dmid=dm_id).exists():
                    #     continue
                    
                    dm_id = d.dmid if d.dmid else f"{d.date}_{d.uhash}"
                    
                    # 发送时间转换
                    naive_send_time = datetime.fromtimestamp(d.date)
                    # 检查 settings.USE_TZ 并转换为 aware datetime
                    if settings.USE_TZ:
                        send_time = timezone.make_aware(naive_send_time, timezone.get_default_timezone())
                    else:
                        send_time = naive_send_time # 如果 USE_TZ=False，则保持 naive
                    
                    # 创建弹幕对象
                    danmaku = Danmaku(
                        video=video_obj,
                        dmid=dm_id,
                        content=d.text,
                        send_time=send_time,
                        progress=d.stime,  # 视频进度，单位为毫秒
                        mode=d.mode,  # 弹幕模式
                        font_size=d.size,  # 字体大小
                        color=f"#{d.color:06x}",  # 颜色，转为十六进制格式
                        user_hash=d.uhash,  # 用户哈希
                        weight=d.weight,  # 弹幕权重
                        page_duration=page_duration,  # 分P时长
                        page_id=page_num  # 分P编号
                    )
                    danmaku_list.append(danmaku)
                    count += 1
                    
                    # 批量保存，每1000条提交一次
                    if len(danmaku_list) >= 1000:
                        Danmaku.objects.bulk_create(danmaku_list, ignore_conflicts=True)
                        danmaku_list = []
                
                # 保存剩余的弹幕
                if danmaku_list:
                    Danmaku.objects.bulk_create(danmaku_list, ignore_conflicts=True)
        
        except Exception as e:
            logger.error(f"解析弹幕异常: {str(e)}")
            return 0
            
        return count
    
    def crawl_danmaku(self, video_url_or_bvid, cookie_str=None, user=None, existing_task=None):
        """爬取视频弹幕的主方法"""
        # 判断输入是BV号还是URL
        if video_url_or_bvid.startswith('http'):
            bvid = self.parse_bvid(video_url_or_bvid)
        else:
            bvid = video_url_or_bvid
        
        if not bvid:
            logger.error("无法解析BV号")
            return None
        
        # 解析Cookie
        cookies = self.parse_bilibili_cookie(cookie_str) if cookie_str else None
        
        # 创建或获取视频对象 - 根据bvid和user的组合查找
        video_obj = None
        video_exists = False
        try:
            # 修改为根据bvid和user的组合查找
            if user:
                video_obj = Video.objects.get(bvid=bvid, user=user)
            else:
                # 如果没有提供user，则尝试查找没有关联用户的视频
                video_obj = Video.objects.get(bvid=bvid, user__isnull=True)
            
            video_exists = True
            # 更新上次爬取时间
            video_obj.last_crawled = timezone.now()
            video_obj.save()
            
            # 如果视频已存在（重新爬取），删除旧弹幕
            logger.info(f"视频 {bvid} 已存在，删除旧弹幕数据...")
            deleted_count, _ = Danmaku.objects.filter(video=video_obj).delete()
            logger.info(f"删除了 {deleted_count} 条旧弹幕")
            
        except Video.DoesNotExist:
            # 获取视频信息
            video_info = self.get_video_info(bvid)
            if not video_info:
                logger.error(f"获取视频信息失败: {bvid}")
                return None
            
            # 创建视频对象，并关联用户
            video_obj = Video.objects.create(
                bvid=video_info['bvid'],
                aid=video_info['aid'],
                title=video_info['title'],
                owner=video_info['owner']['name'],
                owner_mid=video_info['owner']['mid'],
                duration=video_info['duration'],
                last_crawled=timezone.now(),
                user=user  # 设置用户
            )
            video_exists = False
        
        # 使用传入的任务或创建新任务
        task = None
        if existing_task:
            task = existing_task
            # 更新任务状态为运行中
            task.status = 'running'
            task.save()
            logger.info(f"使用现有任务 ID: {task.id}, 视频: {video_obj.title}")
        else:
            # 仅在没有传入任务时创建新任务
            task = CrawlTask.objects.create(
                video=video_obj,
                status='running',
                started_at=timezone.now(),
                user=user  # 设置用户
            )
            logger.info(f"创建新任务 ID: {task.id}, 视频: {video_obj.title}")
        
        try:
            # 获取所有分P的cid
            cid_info_list = self.get_all_cids(bvid)
            if not cid_info_list:
                raise Exception("获取视频分P信息失败")
                
            pid = video_obj.aid
            total_count = 0
            
            # 爬取每个分P的弹幕
            for index, cid_info in enumerate(cid_info_list, start=1):
                cid = cid_info['cid']
                page_duration = cid_info['duration'] # 获取分P时长
                logger.info(f"开始爬取第 {index} 集弹幕数据(cid: {cid})")
                
                # 获取该分P的所有弹幕
                danmakus = self.get_all_danmaku(cid, pid, cookies)
                if not danmakus:
                    logger.info(f"第 {index} 集没有弹幕数据")
                    continue
                
                # 解析并保存弹幕
                count = self.parse_danmaku(danmakus, video_obj, index, page_duration) # 传递分P信息
                total_count += count
                
                logger.info(f"第 {index} 集弹幕保存完成，共 {count} 条")
                time.sleep(2)  # 防止请求过快
            
            # 更新任务状态
            task.status = 'completed'
            task.danmaku_count = total_count
            task.completed_at = timezone.now()
            task.save()
            
            logger.info(f"爬取完成: {video_obj.title}, 共{total_count}条弹幕")
            return task
        
        except Exception as e:
            logger.error(f"爬取弹幕异常: {str(e)}")
            task.status = 'failed'
            task.error_message = str(e)
            task.completed_at = timezone.now()
            task.save()
            return None


# 实例化爬虫
crawler = BilibiliDanmakuCrawler()

def crawl_video_danmaku(video_url_or_bvid, cookie_str=None, user=None, existing_task=None):
    """爬取视频弹幕的快捷函数"""
    return crawler.crawl_danmaku(video_url_or_bvid, cookie_str, user, existing_task) 