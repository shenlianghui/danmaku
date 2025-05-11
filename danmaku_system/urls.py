"""
URL configuration for danmaku_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.views.static import serve
from rest_framework.routers import DefaultRouter
import os
from django.conf import settings

from danmaku_crawler.views import VideoViewSet, DanmakuViewSet, CrawlTaskViewSet
from danmaku_analysis.views import AnalysisViewSet

# 创建路由器
router = DefaultRouter()
router.register(r'videos', VideoViewSet)
router.register(r'danmakus', DanmakuViewSet)
router.register(r'tasks', CrawlTaskViewSet)
router.register(r'analyses', AnalysisViewSet)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    # 添加 accounts 应用的 URL
    path('api/accounts/', include('accounts.urls')),
    # DRF 浏览器API登录
    path('api-auth/', include('rest_framework.urls')),
    # 处理前端静态资源
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    # 处理前端构建的JS文件
    re_path(r'^js/(?P<path>.*)$', serve, {'document_root': os.path.join(settings.FRONTEND_ROOT, 'js')}),
    # 处理前端构建的CSS文件
    re_path(r'^css/(?P<path>.*)$', serve, {'document_root': os.path.join(settings.FRONTEND_ROOT, 'css')}),
    # 将所有其他请求传递给Vue前端
    re_path(r'^.*$', TemplateView.as_view(template_name='index.html')),
]
