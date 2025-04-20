from rest_framework import serializers
from .models import Video, Danmaku, CrawlTask

class VideoSerializer(serializers.ModelSerializer):
    """视频信息序列化器"""
    danmaku_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Video
        fields = ['id', 'bvid', 'aid', 'title', 'owner', 'owner_mid', 
                  'duration', 'created_at', 'last_crawled', 'danmaku_count']
    
    def get_danmaku_count(self, obj):
        return obj.danmakus.count()

class DanmakuSerializer(serializers.ModelSerializer):
    """弹幕数据序列化器"""
    
    class Meta:
        model = Danmaku
        fields = ['id', 'dmid', 'content', 'send_time', 'progress', 'mode', 
                  'font_size', 'color', 'user_hash', 'weight', 'created_at']

class CrawlTaskSerializer(serializers.ModelSerializer):
    """爬取任务序列化器"""
    video_title = serializers.SerializerMethodField()
    video_detail = VideoSerializer(source='video', read_only=True)
    
    class Meta:
        model = CrawlTask
        fields = ['id', 'video', 'video_title', 'video_detail', 'status', 'created_at', 
                  'started_at', 'completed_at', 'danmaku_count', 'error_message']
    
    def get_video_title(self, obj):
        return obj.video.title 
