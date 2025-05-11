from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
import threading
import logging
import traceback
import json

from danmaku_crawler.models import Video
from .models import DanmakuAnalysis
from .serializers import AnalysisSerializer
from .analyzer import analyze_video_danmaku
# 检查BERT模型是否可用
from .bert_sentiment import bert_analyzer

logger = logging.getLogger(__name__)

# 分析任务状态跟踪
analysis_tasks = {}

class AnalysisViewSet(viewsets.ReadOnlyModelViewSet):
    """弹幕分析结果视图集"""
    queryset = DanmakuAnalysis.objects.all().order_by('-created_at')
    serializer_class = AnalysisSerializer
    permission_classes = [permissions.AllowAny]  # 允许所有人访问
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 按视频BV号筛选
        bvid = self.request.query_params.get('bvid', None)
        if bvid:
            video = get_object_or_404(Video, bvid=bvid)
            queryset = queryset.filter(video=video)
        
        # 按分析类型筛选
        analysis_type = self.request.query_params.get('type', None)
        if analysis_type:
            queryset = queryset.filter(analysis_type=analysis_type)
        
        return queryset
    
    def _async_analyze(self, bvid, analysis_type, use_bert, batch_size, max_processing_time):
        """异步执行分析任务"""
        task_id = f"{bvid}_{analysis_type}_{timezone.now().timestamp()}"
        analysis_tasks[task_id] = {"status": "processing", "start_time": timezone.now()}
        
        try:
            # 执行分析
            result = analyze_video_danmaku(
                bvid, 
                analysis_type, 
                use_bert=use_bert, 
                batch_size=batch_size,
                max_processing_time=max_processing_time
            )
            
            # 更新任务状态
            analysis_tasks[task_id] = {
                "status": "completed" if "error" not in result else "failed",
                "result": result,
                "completed_at": timezone.now()
            }
            
            logger.info(f"异步分析任务完成: {task_id}")
        except Exception as e:
            logger.error(f"异步分析任务异常: {task_id}, 错误: {str(e)}")
            logger.error(traceback.format_exc())
            analysis_tasks[task_id] = {
                "status": "failed",
                "error": str(e),
                "completed_at": timezone.now()
            }
    
    @action(detail=False, methods=['post'])
    def analyze(self, request):
        """触发弹幕分析"""
        # 检查用户是否登录
        if not request.user.is_authenticated:
            return Response({
                'message': '您需要登录才能执行分析'
            }, status=status.HTTP_401_UNAUTHORIZED)
            
        # 从请求中获取参数
        bvid = request.data.get('bvid')
        analysis_type = request.data.get('type', None)  # 如果不指定类型，则进行所有分析
        async_mode = request.data.get('async', False)  # 是否异步处理
        use_bert = not request.data.get('force_simple', False)  # 是否使用简单模式（不使用BERT）
        batch_size = request.data.get('batch_size', None)  # BERT批处理大小
        max_processing_time = request.data.get('max_processing_time', 300)  # 最大处理时间(秒)

        logger.info(f"收到分析请求: BV {bvid}, 类型 {analysis_type}, 异步? {async_mode}, 使用BERT? {use_bert}")

        # 验证BV号是否提供
        if not bvid:
            logger.error("缺少视频BV号")
            return Response({
                'message': '缺少视频BV号参数'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 验证分析类型是否有效
        valid_types = ['keyword', 'sentiment', 'timeline', 'user', 'all', None]
        if analysis_type not in valid_types:
            logger.error(f"无效的分析类型: {analysis_type}")
            return Response({
                'message': f'无效的分析类型: {analysis_type}. 有效类型: {", ".join([t for t in valid_types if t])}'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            video = Video.objects.get(bvid=bvid)
            logger.info(f"找到视频: {video.title} (BV: {bvid})")
        except Video.DoesNotExist:
            logger.error(f"视频不存在: {bvid}")
            return Response({
                'message': f'视频不存在: {bvid}'
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            # 检查视频是否有弹幕
            danmaku_count = video.danmakus.count()
            if danmaku_count == 0:
                logger.warning(f"视频没有弹幕数据: {bvid}")
                return Response({
                    'message': f'视频没有弹幕数据，请先爬取弹幕'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            logger.info(f"开始分析视频 {bvid}, 弹幕数: {danmaku_count}, 分析类型: {analysis_type}")
            
            # 添加BERT模型状态信息
            bert_available = bert_analyzer.is_model_loaded()
            
            # 检查是否有缓存的分析结果
            cached_analysis = None
            if analysis_type:
                try:
                    cached_analysis = DanmakuAnalysis.objects.get(
                        video=video, 
                        analysis_type=analysis_type
                    )
                except DanmakuAnalysis.DoesNotExist:
                    pass
            
            # 如果存在缓存且不是异步任务，直接返回缓存的结果
            if cached_analysis and not async_mode:
                logger.info(f"使用缓存的分析结果: {bvid}, 类型: {analysis_type}")
                result_json = cached_analysis.result_json

                # 确保返回数据中的列表数据有正确的row属性
                if analysis_type == 'keyword' and isinstance(result_json, list):
                    for idx, item in enumerate(result_json):
                        item['row'] = idx  # 添加row字段
                
                elif analysis_type == 'timeline' and isinstance(result_json, dict) and 'timeline' in result_json:
                    # 确保时间线数据中的每个元素都有row字段
                    if isinstance(result_json['timeline'], list):
                        for idx, item in enumerate(result_json['timeline']):
                            item['row'] = idx
                    
                    # 为高峰数据添加row字段
                    if 'peaks' in result_json and isinstance(result_json['peaks'], list):
                        for idx, item in enumerate(result_json['peaks']):
                            item['row'] = idx
                
                elif analysis_type == 'user_activity' and isinstance(result_json, dict) and 'top_users' in result_json:
                    # 为用户活跃度数据添加row字段
                    if isinstance(result_json['top_users'], list):
                        for idx, item in enumerate(result_json['top_users']):
                            item['row'] = idx
                
                # 处理情感分析结果
                elif analysis_type == 'sentiment' and isinstance(result_json, dict):
                    # 确保segments数组中的每个元素都有row字段
                    if 'segments' in result_json and isinstance(result_json['segments'], list):
                        for idx, item in enumerate(result_json['segments']):
                            item['row'] = idx
                
                return Response({
                    'message': f'使用缓存的分析结果: {video.title}',
                    'result': result_json,
                    'cached': True,
                    'bert_model': {
                        'available': bert_available,
                        'used': result_json.get('used_bert', False) if hasattr(result_json, 'get') else False
                    }
                })
            
            # 处理异步请求
            if async_mode:
                task_id = f"{bvid}_{analysis_type}_{timezone.now().timestamp()}"
                # 启动异步线程
                thread = threading.Thread(
                    target=self._async_analyze,
                    args=(bvid, analysis_type, use_bert, batch_size, max_processing_time)
                )
                thread.daemon = True  # 设为守护线程
                thread.start()
                
                return Response({
                    'message': f'分析任务已启动: {video.title}',
                    'task_id': task_id,
                    'status': 'processing'
                })
            
            # 同步模式下执行分析
            result = analyze_video_danmaku(
                bvid, 
                analysis_type, 
                use_bert=use_bert, 
                batch_size=batch_size,
                max_processing_time=max_processing_time
            )
            
            if 'error' in result:
                logger.error(f"分析失败: {result['error']}")
                return Response({
                    'message': f'分析失败: {result["error"]}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 处理返回数据，添加row属性
            if analysis_type == 'keyword' and isinstance(result, list):
                for idx, item in enumerate(result):
                    item['row'] = idx
            
            elif analysis_type == 'timeline' and isinstance(result, dict) and 'timeline' in result:
                # 确保时间线数据中的每个元素都有row字段
                if isinstance(result['timeline'], list):
                    for idx, item in enumerate(result['timeline']):
                        item['row'] = idx
                
                # 为高峰数据添加row字段
                if 'peaks' in result and isinstance(result['peaks'], list):
                    for idx, item in enumerate(result['peaks']):
                        item['row'] = idx
            
            elif analysis_type == 'user_activity' and isinstance(result, dict) and 'top_users' in result:
                # 为用户活跃度数据添加row字段
                if isinstance(result['top_users'], list):
                    for idx, item in enumerate(result['top_users']):
                        item['row'] = idx
            
            # 处理情感分析结果
            elif analysis_type == 'sentiment' and isinstance(result, dict):
                # 确保segments数组中的每个元素都有row字段
                if 'segments' in result and isinstance(result['segments'], list):
                    for idx, item in enumerate(result['segments']):
                        item['row'] = idx
            
            # 全部分析时，需要处理每个子结果
            elif analysis_type is None and isinstance(result, dict):
                # 处理关键词
                if 'keywords' in result and isinstance(result['keywords'], list):
                    for idx, item in enumerate(result['keywords']):
                        item['row'] = idx
                
                # 处理时间线
                if 'timeline' in result and isinstance(result['timeline'], dict):
                    if 'timeline' in result['timeline'] and isinstance(result['timeline']['timeline'], list):
                        for idx, item in enumerate(result['timeline']['timeline']):
                            item['row'] = idx
                    if 'peaks' in result['timeline'] and isinstance(result['timeline']['peaks'], list):
                        for idx, item in enumerate(result['timeline']['peaks']):
                            item['row'] = idx
                
                # 处理用户活跃度
                if 'user_activity' in result and isinstance(result['user_activity'], dict):
                    if 'top_users' in result['user_activity'] and isinstance(result['user_activity']['top_users'], list):
                        for idx, item in enumerate(result['user_activity']['top_users']):
                            item['row'] = idx
                
                # 处理情感分析
                if 'sentiment' in result and isinstance(result['sentiment'], dict):
                    if 'segments' in result['sentiment'] and isinstance(result['sentiment']['segments'], list):
                        for idx, item in enumerate(result['sentiment']['segments']):
                            item['row'] = idx
            
            # 获取BERT性能统计信息
            bert_stats = None
            if bert_available and use_bert:
                bert_stats = bert_analyzer.get_performance_stats()
            
            # 在响应中添加BERT模型使用信息
            response_data = {
                'message': f'分析完成: {video.title}',
                'result': result,
                'bert_model': {
                    'available': bert_available,
                    'used': use_bert and bert_available and (analysis_type == 'sentiment' or analysis_type is None),
                    'performance': bert_stats
                }
            }
            
            logger.info(f"分析完成: {bvid}, 类型: {analysis_type}")
            return Response(response_data)
        
        except Exception as e:
            logger.error(f"分析过程发生异常: {str(e)}")
            logger.error(traceback.format_exc())
            return Response({
                'message': f'分析失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def task_status(self, request):
        """获取异步任务状态"""
        task_id = request.query_params.get('task_id', None)
        
        if not task_id:
            # 返回所有任务状态
            return Response({
                'tasks': analysis_tasks
            })
        
        # 返回指定任务状态
        if task_id in analysis_tasks:
            task_data = analysis_tasks[task_id]
            # 如果任务已完成，清理过期任务
            if task_data.get('status') in ['completed', 'failed'] and 'completed_at' in task_data:
                # 计算任务完成时间超过1小时的任务
                completed_time = task_data['completed_at']
                if (timezone.now() - completed_time).total_seconds() > 3600:
                    # 延迟清理 - 只记录日志，不实际删除，避免刚好请求时删除导致找不到任务
                    logger.info(f"任务已过期，将在下次清理: {task_id}")
            
            return Response(task_data)
        
        return Response({
            'message': f'任务不存在: {task_id}'
        }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'])
    def clear_bert_cache(self, request):
        """清除BERT模型缓存"""
        if not bert_analyzer.is_model_loaded():
            return Response({
                'message': 'BERT模型未加载，无缓存可清除'
            })
        
        cache_cleared = bert_analyzer.clear_cache()
        
        return Response({
            'message': '缓存清除成功' if cache_cleared else 'BERT缓存未启用',
            'cache_stats': {
                'enabled': bert_analyzer.cache_enabled,
                'size': len(bert_analyzer.result_cache) if bert_analyzer.cache_enabled else 0
            }
        })
    
    @action(detail=False, methods=['get'])
    def bert_status(self, request):
        """获取BERT模型状态"""
        is_loaded = bert_analyzer.is_model_loaded()
        
        response_data = {
            'loaded': is_loaded,
            'device': str(bert_analyzer.device) if is_loaded else None,
        }
        
        # 如果模型已加载，添加更多信息
        if is_loaded:
            response_data.update({
                'performance': bert_analyzer.get_performance_stats(),
                'cache': {
                    'enabled': bert_analyzer.cache_enabled,
                    'size': len(bert_analyzer.result_cache) if bert_analyzer.cache_enabled else 0,
                    'max_size': bert_analyzer.cache_size if bert_analyzer.cache_enabled else 0
                }
            })
        
        return Response(response_data)
    
    @action(detail=False, methods=['post'])
    def cleanup_tasks(self, request):
        """清理过期的任务状态"""
        # 清理已完成且超过1小时的任务
        current_time = timezone.now()
        expired_tasks = []
        
        for task_id, task_data in list(analysis_tasks.items()):
            if task_data.get('status') in ['completed', 'failed'] and 'completed_at' in task_data:
                completed_time = task_data['completed_at']
                if (current_time - completed_time).total_seconds() > 3600:
                    expired_tasks.append(task_id)
                    del analysis_tasks[task_id]
        
        return Response({
            'message': f'清理了 {len(expired_tasks)} 个过期任务',
            'cleaned_tasks': expired_tasks,
            'remaining_tasks': len(analysis_tasks)
        })

    @action(detail=False, methods=['get'])
    def config(self, request):
        """获取弹幕分析配置"""
        from . import analyzer_config
        
        # 不直接返回配置中的集合类型(set)，转换为列表
        positive_words = list(analyzer_config.POSITIVE_WORDS) if hasattr(analyzer_config, 'POSITIVE_WORDS') else []
        negative_words = list(analyzer_config.NEGATIVE_WORDS) if hasattr(analyzer_config, 'NEGATIVE_WORDS') else []
        
        # 返回配置信息
        config_data = {
            'sentiment_analysis': analyzer_config.SENTIMENT_ANALYSIS,
            'keyword_analysis': analyzer_config.KEYWORD_ANALYSIS,
            'timeline_analysis': analyzer_config.TIMELINE_ANALYSIS,
            'user_activity': analyzer_config.USER_ACTIVITY,
            'bert_config': analyzer_config.BERT_CONFIG,
            'performance': analyzer_config.PERFORMANCE,
            'word_lists': {
                'positive_words_count': len(positive_words),
                'negative_words_count': len(negative_words),
                # 只返回部分词汇作为示例
                'positive_words_sample': positive_words[:20] if positive_words else [],
                'negative_words_sample': negative_words[:20] if negative_words else [],
            }
        }
        
        # 添加BERT模型状态
        is_loaded = bert_analyzer.is_model_loaded()
        config_data['bert_status'] = {
            'loaded': is_loaded,
            'device': str(bert_analyzer.device) if is_loaded else 'none',
        }
        
        return Response(config_data)
