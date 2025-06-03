from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
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
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        """根据用户和查询参数过滤视频列表。"""
        queryset = super().get_queryset() # Video.objects.all().order_by('-created_at')

        if not self.request.user.is_authenticated:
            return Video.objects.none()

        user_param = self.request.query_params.get('user', 'current')
        if user_param == 'all' and self.request.user.is_staff:
            pass # 管理员查看所有
        else: # 包含 'current' 或特定用户ID (如果支持)
            queryset = queryset.filter(user=self.request.user)

        # **关键的 BVID 过滤**
        bvid_param = self.request.query_params.get('bvid', None)
        if bvid_param:
            # 这个过滤应该确保在应用了用户过滤后，只留下具有特定 BVID 的视频。
            # 由于 (bvid, user) 是 unique_together, 理论上这里最多只会有一条记录。
            queryset = queryset.filter(bvid=bvid_param)
        
        search_param = self.request.query_params.get('search', None)
        if search_param:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(title__icontains=search_param) | 
                Q(bvid__icontains=search_param) |
                Q(owner__icontains=search_param)
            )
        
        # 对于列表视图，保持排序。对于 getVideoByBvid 的调用，我们期望只有一个结果。
        return queryset
    
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
        
        # 非管理员只能看到自己的任务
        if not request.user.is_staff:
            tasks = CrawlTask.objects.filter(video=video, user=request.user).order_by('-created_at')
        else:
            tasks = CrawlTask.objects.filter(video=video).order_by('-created_at')
            
        serializer = CrawlTaskSerializer(tasks, many=True)
        return Response(serializer.data)
        


class DanmakuViewSet(viewsets.ReadOnlyModelViewSet):
    """弹幕数据视图集"""
    queryset = Danmaku.objects.all().order_by('progress')
    serializer_class = DanmakuSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        if not self.request.user.is_authenticated:
            return Danmaku.objects.none()
        
        # 按视频BV号筛选
        bvid = self.request.query_params.get('bvid', None)
        if bvid:
            video = get_object_or_404(Video, bvid=bvid)
            queryset = queryset.filter(video=video)
            
        # 用户过滤逻辑
        user_param = self.request.query_params.get('user', None)
        if user_param == 'all' and self.request.user.is_staff:
            # 管理员请求'all'时返回所有弹幕
            pass
        else:
            # 其他情况只返回用户自己视频的弹幕
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
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        """根据用户过滤任务列表"""
        queryset = super().get_queryset()
        
        if not self.request.user.is_authenticated:
            return CrawlTask.objects.none()
        
        # 如果请求参数中有视频ID，过滤出该视频的任务
        video_id = self.request.query_params.get('video', None)
        if video_id:
            queryset = queryset.filter(video_id=video_id)
        
        # 用户过滤逻辑
        user_param = self.request.query_params.get('user', None)
        if user_param == 'all' and self.request.user.is_staff:
            # 管理员可以查看所有任务
            return queryset
        
        # 其他用户只能查看自己的任务
        return queryset.filter(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def create_task(self, request):
        """创建新的爬取任务"""
        if not request.user.is_authenticated:
            return Response({
                'message': '您需要登录才能创建爬取任务'
            }, status=status.HTTP_401_UNAUTHORIZED)
            
        try:
            video_url = request.data.get('video_url', None)
            cookie_str = request.data.get('cookie_str', None)
            
            if not video_url:
                return Response({
                    'message': '请提供视频URL'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 解析BV号
            crawler = BilibiliDanmakuCrawler()
            bvid = crawler.parse_bvid(video_url) if video_url.startswith('http') else video_url
                
            if not bvid:
                return Response({
                    'message': '无法解析BV号，请检查URL格式'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取视频信息
            video_info = crawler.get_video_info(bvid)
            if not video_info:
                return Response({
                    'message': '获取视频信息失败，请检查URL或Cookie是否正确'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取或创建视频记录
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
            
            # 创建爬取任务
            task = CrawlTask.objects.create(
                video=video_obj,
                status='pending',
                started_at=timezone.now(),
                user=request.user
            )
            
            # 启动后台爬取任务
            def run_crawler_task():
                try:
                    logger.info(f"开始后台爬取任务 ID: {task.id}, 视频: {video_obj.title}")
                    task.status = 'running'
                    task.save()
                    
                    result = crawl_video_danmaku(bvid, cookie_str=cookie_str, user=request.user, existing_task=task)
                    
                    # 更新任务状态
                    task.refresh_from_db()
                    if task.status == 'running':
                        if result:
                            task.status = 'completed'
                            task.danmaku_count = result.danmaku_count
                        else:
                            task.status = 'failed'
                            task.error_message = '爬取过程中出现错误'
                        task.completed_at = timezone.now()
                        task.save()
                        video_obj.save()
                except Exception as e:
                    logger.exception(f"后台爬取任务异常 - 任务ID: {task.id}, 异常: {str(e)}")
                    try:
                        task.refresh_from_db()
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
                'message': f'已提交爬取任务 - {video_obj.title}',
                'task_id': task.id,
                'status': 'pending'
            })
            
        except Exception as e:
            logger.exception(f"爬取任务创建异常 - 用户: {request.user.username}, 异常: {str(e)}")
            return Response({
                'message': f'爬取任务创建失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    @action(detail=False, methods=['get'])
    def my_tasks(self, request):
        """获取当前用户的所有爬取任务"""
        if not request.user.is_authenticated:
            return Response({
                'message': '您需要登录才能查看任务'
            }, status=status.HTTP_401_UNAUTHORIZED)
            
        tasks = CrawlTask.objects.filter(user=request.user).order_by('-created_at')
        page = self.paginate_queryset(tasks)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)


