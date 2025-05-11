from django.contrib import admin
from .models import DanmakuAnalysis

@admin.register(DanmakuAnalysis)
class AnalysisAdmin(admin.ModelAdmin):
    list_display = ('video', 'analysis_type', 'created_at', 'updated_at')
    search_fields = ('video__title', 'video__bvid')
    list_filter = ('analysis_type', 'created_at')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('video',)

