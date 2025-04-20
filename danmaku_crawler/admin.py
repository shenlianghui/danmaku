from django.contrib import admin
from .models import Video, Danmaku, CrawlTask

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'bvid', 'owner', 'duration', 'created_at', 'last_crawled')
    search_fields = ('title', 'bvid', 'owner')
    list_filter = ('created_at', 'last_crawled')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)

@admin.register(Danmaku)
class DanmakuAdmin(admin.ModelAdmin):
    list_display = ('content', 'video', 'progress', 'send_time', 'mode', 'color')
    search_fields = ('content', 'video__title', 'video__bvid')
    list_filter = ('send_time', 'mode', 'color')
    date_hierarchy = 'send_time'
    readonly_fields = ('created_at',)
    raw_id_fields = ('video',)

@admin.register(CrawlTask)
class CrawlTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'video', 'status', 'created_at', 'started_at', 'completed_at', 'danmaku_count')
    search_fields = ('video__title', 'video__bvid', 'error_message')
    list_filter = ('status', 'created_at')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
    raw_id_fields = ('video',)
