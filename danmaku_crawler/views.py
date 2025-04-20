from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import JsonResponse
import json
import logging
from django.utils import timezone
from threading import Thread

from .models import Video, Danmaku, CrawlTask
from .serializers import VideoSerializer, DanmakuSerializer, CrawlTaskSerializer
from .crawler import crawl_video_danmaku, BilibiliDanmakuCrawler

logger = logging.getLogger(__name__)

class VideoViewSet(viewsets.ModelViewSet):
    """视频信息视图集"""
    queryset = Video.objects.all().order_by('-created_at')
    serializer_class = VideoSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """根据用户过滤视频列表"""
        queryset = super().get_queryset()
        
        # 用户过滤逻辑
        user_param = self.request.query_params.get('user', None)
        
        # 如果明确指定获取当前用户视频，或者默认情况下非管理员用户
        if user_param == 'current' or (user_param != 'all' and not self.request.user.is_staff):
            queryset = queryset.filter(user=self.request.user)
        # 只有管理员在明确请求时才能看到所有视频
        elif user_param == 'all' and not self.request.user.is_staff:
            # 非管理员请求所有视频时，仍然只返回自己的视频
            queryset = queryset.filter(user=self.request.user)
            
        return queryset
    
    @action(detail=True, methods=['post'])
    def crawl(self, request, pk=None):
        """触发爬取视频弹幕"""
        video = self.get_object()
        
        # 创建一个任务对象
        task = CrawlTask.objects.create(
            video=video,
            status='pending',
            started_at=timezone.now(),
            user=request.user
        )
        
        # 启动后台任务
        def run_crawler_task():
            try:
                # 修改任务状态为运行中
                task.status = 'running'
                task.save()
                
                # 传递当前用户和任务对象到爬取方法
                result = crawl_video_danmaku(video.bvid, user=request.user, existing_task=task)
                
                # 任务完成后会自动更新状态
            except Exception as e:
                logger.exception(f"爬取弹幕异常 - 视频: {video.title}, 异常: {str(e)}")
                try:
                    # 更新任务状态为失败
                    task.refresh_from_db()
                    if task.status == 'running':
                        task.status = 'failed'
                        task.error_message = str(e)
                        task.completed_at = timezone.now()
                        task.save()
                except Exception as inner_e:
                    logger.error(f"更新任务状态失败: {str(inner_e)}")
        
        # 启动爬取线程
        crawler_thread = Thread(target=run_crawler_task)
        crawler_thread.daemon = True
        crawler_thread.start()
        
        return Response({
            'message': f'已开始爬取弹幕 - {video.title}',
            'task_id': task.id,
            'status': task.status
        })
    
    @action(detail=True, methods=['get'])
    def danmakus(self, request, pk=None):
        """获取视频的所有弹幕"""
        video = self.get_object()
        danmakus = Danmaku.objects.filter(video=video).order_by('progress')
        
        page = self.paginate_queryset(danmakus)
        if page is not None:
            serializer = DanmakuSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = DanmakuSerializer(danmakus, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def tasks(self, request, pk=None):
        """获取视频的所有爬取任务"""
        video = self.get_object()
        
        # 获取任务时也要根据用户过滤，只返回当前用户的任务
        if not request.user.is_staff:  # 非管理员只能看到自己的任务
            tasks = CrawlTask.objects.filter(video=video, user=request.user).order_by('-created_at')
        else:
            # 管理员可以看到所有任务
            tasks = CrawlTask.objects.filter(video=video).order_by('-created_at')
            
        serializer = CrawlTaskSerializer(tasks, many=True)
        return Response(serializer.data)
        
    @action(detail=False, methods=['get'])
    def my_videos(self, request):
        """获取当前用户的所有视频"""
        # 明确指定查询当前用户的视频
        videos = Video.objects.filter(user=request.user).order_by('-created_at')
        page = self.paginate_queryset(videos)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(videos, many=True)
        return Response(serializer.data)

class DanmakuViewSet(viewsets.ReadOnlyModelViewSet):
    """弹幕数据视图集"""
    queryset = Danmaku.objects.all().order_by('progress')
    serializer_class = DanmakuSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 按视频BV号筛选
        bvid = self.request.query_params.get('bvid', None)
        if bvid:
            video = get_object_or_404(Video, bvid=bvid)
            queryset = queryset.filter(video=video)
        
        # 用户过滤逻辑
        user_param = self.request.query_params.get('user', None)
        
        # 如果明确指定获取当前用户弹幕，或者默认情况下非管理员用户
        if user_param == 'current' or (user_param != 'all' and not self.request.user.is_staff):
            queryset = queryset.filter(video__user=self.request.user)
        # 只有管理员在明确请求时才能看到所有弹幕
        elif user_param == 'all' and not self.request.user.is_staff:
            # 非管理员请求所有弹幕时，仍然只返回自己视频的弹幕
            queryset = queryset.filter(video__user=self.request.user)
        
        # 按进度范围筛选
        start = self.request.query_params.get('start', None)
        end = self.request.query_params.get('end', None)
        
        if start:
            queryset = queryset.filter(progress__gte=float(start))
        if end:
            queryset = queryset.filter(progress__lte=float(end))
        
        return queryset

class CrawlTaskViewSet(viewsets.ReadOnlyModelViewSet):
    """爬取任务视图集"""
    queryset = CrawlTask.objects.all().order_by('-created_at')
    serializer_class = CrawlTaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """根据用户过滤任务列表"""
        queryset = super().get_queryset()
        
        # 如果请求参数中有视频ID，过滤出该视频的任务
        video_id = self.request.query_params.get('video', None)
        if video_id:
            queryset = queryset.filter(video_id=video_id)
        
        # 用户过滤逻辑
        user_param = self.request.query_params.get('user', None)
        
        # 如果明确指定获取当前用户任务，或者默认情况下非管理员用户
        if user_param == 'current' or (user_param != 'all' and not self.request.user.is_staff):
            queryset = queryset.filter(user=self.request.user)
        # 只有管理员在明确请求时才能看到所有任务
        elif user_param == 'all' and not self.request.user.is_staff:
            # 非管理员请求所有任务时，仍然只返回自己的任务
            queryset = queryset.filter(user=self.request.user)
            
        return queryset
    
    @action(detail=False, methods=['post'])
    def create_task(self, request):
        """创建新的爬取任务"""
        try:
            video_url = request.data.get('video_url', None)
            cookie_str = request.data.get('cookie_str', None)
            
            if not video_url:
                return Response({
                    'message': '请提供视频URL'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 首先尝试解析BV号，以验证URL格式
            crawler = BilibiliDanmakuCrawler()
            bvid = None
            
            if video_url.startswith('http'):
                bvid = crawler.parse_bvid(video_url)
            else:
                bvid = video_url
                
            if not bvid:
                return Response({
                    'message': '无法解析BV号，请检查URL格式'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 先获取视频基本信息，确认视频存在
            video_info = crawler.get_video_info(bvid)
            if not video_info:
                return Response({
                    'message': f'获取视频信息失败，请检查URL或Cookie是否正确'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 创建视频记录（如果不存在）
            video_obj = None
            try:
                video_obj = Video.objects.get(bvid=bvid, user=request.user)
                logger.info(f"视频已存在: {bvid}, 用户: {request.user.username}")
            except Video.DoesNotExist:
                # 创建新视频记录
                video_obj = Video.objects.create(
                    bvid=video_info['bvid'],
                    aid=video_info['aid'],
                    title=video_info['title'],
                    owner=video_info['owner']['name'],
                    owner_mid=video_info['owner']['mid'],
                    duration=video_info['duration'],
                    last_crawled=timezone.now(),
                    user=request.user
                )
                logger.info(f"创建新视频记录: {video_obj.title}, BV: {bvid}")
            
            # 创建爬取任务记录
            task = CrawlTask.objects.create(
                video=video_obj,
                status='pending',  # 设置为等待状态
                started_at=timezone.now(),
                user=request.user
            )
            
            # 启动后台任务
            def run_crawler_task():
                try:
                    logger.info(f"开始后台爬取任务 ID: {task.id}, 视频: {video_obj.title}")
                    # 修改任务状态为运行中
                    task.status = 'running'
                    task.save()
                    
                    # 执行爬取
                    result = crawler.crawl_danmaku(bvid, cookie_str=cookie_str, user=request.user, existing_task=task)
                    
                    # 如果原任务对象已经被更新（如爬取完成或失败），不再更新状态
                    task.refresh_from_db()
                    if task.status == 'running':
                        if result:
                            # 爬取成功，更新状态为已完成
                            task.status = 'completed'
                            task.danmaku_count = result.danmaku_count
                            task.completed_at = timezone.now()
                        else:
                            # 爬取失败
                            task.status = 'failed'
                            task.error_message = '爬取过程中出现错误'
                            task.completed_at = timezone.now()
                        task.save()
                except Exception as e:
                    logger.exception(f"后台爬取任务异常 - 任务ID: {task.id}, 异常: {str(e)}")
                    try:
                        # 更新任务状态为失败
                        task.refresh_from_db()
                        task.status = 'failed'
                        task.error_message = str(e)
                        task.completed_at = timezone.now()
                        task.save()
                    except Exception as inner_e:
                        logger.error(f"更新任务状态失败: {str(inner_e)}")
            
            # 启动爬取线程
            crawler_thread = Thread(target=run_crawler_task)
            crawler_thread.daemon = True  # 设置为守护线程，不阻止主程序退出
            crawler_thread.start()
            
            # 立即返回响应
            return Response({
                'message': f'已提交爬取任务 - {video_obj.title}',
                'task_id': task.id,
                'status': 'pending'
            })
            
        except Exception as e:
            # 记录详细错误信息
            logger.exception(f"爬取任务创建异常 - 用户: {request.user.username}, URL: {video_url if 'video_url' in locals() else 'unknown'}, 异常: {str(e)}")
            return Response({
                'message': f'爬取任务创建失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    @action(detail=False, methods=['get'])
    def my_tasks(self, request):
        """获取当前用户的所有爬取任务"""
        tasks = CrawlTask.objects.filter(user=request.user).order_by('-created_at')
        page = self.paginate_queryset(tasks)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)


