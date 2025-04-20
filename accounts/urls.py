from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('user/', views.UserView.as_view(), name='user'), # 获取当前用户信息
    path('update/', views.UpdateUserView.as_view(), name='update'), # 更新用户信息
    path('check-username/', views.check_username, name='check-username'), # 检查用户名是否可用
    path('csrf/', views.get_csrf_token, name='csrf-token'), # 获取CSRF令牌
    
    # 密码重置
    path('password-reset/', views.PasswordResetView.as_view(), name='password-reset'),
    path('password-reset/confirm/', views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
] 