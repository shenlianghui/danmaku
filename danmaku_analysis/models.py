from django.db import models
from django.utils import timezone
from danmaku_crawler.models import Video

class DanmakuAnalysis(models.Model):
    """弹幕分析结果模型"""
    TYPE_CHOICES = (
        ('sentiment', '情感分析'),
        ('keyword', '关键词分析'),
        ('timeline', '时间线分析'),
        ('user', '用户分析'),
        ('custom', '自定义分析'),
    )
    
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='analyses', verbose_name="分析视频")
    analysis_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="分析类型")
    result_json = models.JSONField(verbose_name="分析结果JSON")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        verbose_name = "弹幕分析"
        verbose_name_plural = "弹幕分析"
        ordering = ['-created_at']
        unique_together = ('video', 'analysis_type')
    
    def __str__(self):
        return f"{self.video.title} - {self.get_analysis_type_display()}"

class KeywordExtraction(models.Model):
    """关键词提取结果模型"""
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='keywords', verbose_name="视频")
    keyword = models.CharField(max_length=50, verbose_name="关键词")
    weight = models.FloatField(verbose_name="权重")
    frequency = models.IntegerField(verbose_name="出现频率")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    
    class Meta:
        verbose_name = "关键词提取"
        verbose_name_plural = "关键词提取"
        ordering = ['-weight']
        unique_together = ('video', 'keyword')
    
    def __str__(self):
        return f"{self.keyword} ({self.weight:.2f})"

class SentimentAnalysis(models.Model):
    """情感分析结果模型"""
    SENTIMENT_CHOICES = (
        ('positive', '积极'),
        ('neutral', '中性'),
        ('negative', '消极'),
    )
    
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='sentiments', verbose_name="视频")
    segment_start = models.FloatField(verbose_name="片段开始时间(秒)")
    segment_end = models.FloatField(verbose_name="片段结束时间(秒)")
    sentiment = models.CharField(max_length=10, choices=SENTIMENT_CHOICES, verbose_name="情感倾向")
    score = models.FloatField(verbose_name="情感得分")
    danmaku_count = models.IntegerField(verbose_name="弹幕数量")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    
    class Meta:
        verbose_name = "情感分析"
        verbose_name_plural = "情感分析"
        ordering = ['segment_start']
    
    def __str__(self):
        return f"{self.video.title} {self.segment_start}-{self.segment_end}秒 ({self.get_sentiment_display()})"
