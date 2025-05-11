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


