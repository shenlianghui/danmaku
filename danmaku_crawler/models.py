from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class Video(models.Model):
    """视频信息模型"""
    bvid = models.CharField(max_length=20, verbose_name="BV号")
    aid = models.BigIntegerField(null=True, blank=True, verbose_name="AV号")
    title = models.CharField(max_length=200, verbose_name="视频标题")
    owner = models.CharField(max_length=100, verbose_name="UP主")
    owner_mid = models.BigIntegerField(null=True, blank=True, verbose_name="UP主ID")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    duration = models.IntegerField(default=0, verbose_name="视频时长(秒)")
    last_crawled = models.DateTimeField(null=True, blank=True, verbose_name="上次爬取时间")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='videos', null=True, blank=True, verbose_name="爬取用户")
    danmaku_count = models.IntegerField(default=0, verbose_name="爬取弹幕数")
    
    class Meta:
        verbose_name = "视频信息"
        verbose_name_plural = "视频信息"
        ordering = ['-created_at']
        # 添加联合唯一约束，确保每个用户的每个视频只有一条记录
        unique_together = ('bvid', 'user')
    
    def __str__(self):
        return f"{self.title} ({self.bvid})"

class Danmaku(models.Model):
    """弹幕数据模型"""
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='danmakus', verbose_name="所属视频")
    page_id = models.IntegerField(default=1, verbose_name="分P编号")
    page_duration = models.IntegerField(default=0, verbose_name="分P时长(秒)")
    dmid = models.BigIntegerField(unique=True, verbose_name="弹幕ID")
    content = models.TextField(verbose_name="弹幕内容")
    send_time = models.DateTimeField(verbose_name="发送时间")
    progress = models.FloatField(verbose_name="视频进度(毫秒)")
    mode = models.IntegerField(default=1, verbose_name="弹幕模式")
    font_size = models.IntegerField(default=25, verbose_name="字体大小")
    color = models.CharField(max_length=10, default="16777215", verbose_name="弹幕颜色")
    user_hash = models.CharField(max_length=32, verbose_name="用户哈希")
    weight = models.IntegerField(default=10, verbose_name="弹幕权重")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="记录时间")
    
    class Meta:
        verbose_name = "弹幕数据"
        verbose_name_plural = "弹幕数据"
        ordering = ['progress']
        indexes = [
            models.Index(fields=['video', 'progress']),
            models.Index(fields=['send_time']),
            models.Index(fields=['page_id']),
        ]
    
    def __str__(self):
        return f"{self.content[:20]}... ({self.progress}s)"

class CrawlTask(models.Model):
    """爬取任务模型"""
    STATUS_CHOICES = (
        ('pending', '等待中'),
        ('running', '进行中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    )
    
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='crawl_tasks', verbose_name="目标视频")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="任务状态")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")
    danmaku_count = models.IntegerField(default=0, verbose_name="爬取弹幕数")
    error_message = models.TextField(blank=True, verbose_name="错误信息")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='crawl_tasks', null=True, blank=True, verbose_name="执行用户")
    
    class Meta:
        verbose_name = "爬取任务"
        verbose_name_plural = "爬取任务"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"任务 {self.id} - {self.video.title} ({self.status})"
