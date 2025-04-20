from rest_framework import serializers
from .models import DanmakuAnalysis, KeywordExtraction, SentimentAnalysis
from danmaku_crawler.serializers import VideoSerializer

class AnalysisSerializer(serializers.ModelSerializer):
    """弹幕分析结果序列化器"""
    video_info = VideoSerializer(source='video', read_only=True)
    analysis_type_display = serializers.SerializerMethodField()
    video_bvid = serializers.SerializerMethodField()
    
    class Meta:
        model = DanmakuAnalysis
        fields = ['id', 'video', 'video_info', 'video_bvid', 'analysis_type', 'analysis_type_display', 
                  'result_json', 'created_at', 'updated_at']
    
    def get_analysis_type_display(self, obj):
        return obj.get_analysis_type_display()
        
    def get_video_bvid(self, obj):
        return obj.video.bvid if obj.video else None

class KeywordSerializer(serializers.ModelSerializer):
    """关键词提取结果序列化器"""
    video_title = serializers.SerializerMethodField()
    
    class Meta:
        model = KeywordExtraction
        fields = ['id', 'video', 'video_title', 'keyword', 'weight', 'frequency', 'created_at']
    
    def get_video_title(self, obj):
        return obj.video.title

class SentimentSerializer(serializers.ModelSerializer):
    """情感分析结果序列化器"""
    video_title = serializers.SerializerMethodField()
    sentiment_display = serializers.SerializerMethodField()
    
    class Meta:
        model = SentimentAnalysis
        fields = ['id', 'video', 'video_title', 'segment_start', 'segment_end', 
                  'sentiment', 'sentiment_display', 'score', 'danmaku_count', 'created_at']
    
    def get_video_title(self, obj):
        return obj.video.title
    
    def get_sentiment_display(self, obj):
        return obj.get_sentiment_display() 
