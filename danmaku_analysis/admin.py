from django.contrib import admin
from .models import DanmakuAnalysis, KeywordExtraction, SentimentAnalysis

@admin.register(DanmakuAnalysis)
class AnalysisAdmin(admin.ModelAdmin):
    list_display = ('video', 'analysis_type', 'created_at', 'updated_at')
    search_fields = ('video__title', 'video__bvid')
    list_filter = ('analysis_type', 'created_at')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('video',)

@admin.register(KeywordExtraction)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ('keyword', 'video', 'weight', 'frequency', 'created_at')
    search_fields = ('keyword', 'video__title', 'video__bvid')
    list_filter = ('created_at',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
    raw_id_fields = ('video',)

@admin.register(SentimentAnalysis)
class SentimentAdmin(admin.ModelAdmin):
    list_display = ('video', 'segment_start', 'segment_end', 'sentiment', 'score', 'danmaku_count')
    search_fields = ('video__title', 'video__bvid')
    list_filter = ('sentiment', 'created_at')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
    raw_id_fields = ('video',)
