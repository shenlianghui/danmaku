from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .serializers import UserSerializer, RegisterSerializer, LoginSerializer, UserUpdateSerializer
from rest_framework import serializers
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse
from django.core.cache import cache
from django.utils import timezone
import datetime

# Create your views here.

# 获取CSRF令牌
@api_view(['GET'])
@ensure_csrf_cookie
def get_csrf_token(request):
    """
    这个视图不做任何事情，只是确保为请求设置了CSRF cookie。
    前端可以调用此端点来获取CSRF令牌。
    """
    return JsonResponse({"message": "CSRF cookie set", "status": "success"})

# 注册视图
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            
            # 注册成功后自动登录
            login(request, user)
            
            # 清除IP登录失败记录（如果有）
            client_ip = self._get_client_ip(request)
            cache_key = f"login_attempts_{client_ip}"
            cache.delete(cache_key)
            
            headers = self.get_success_headers(serializer.data)
            return Response({
                "user": UserSerializer(user).data,
                "message": "用户注册成功并已登录",
                "status": "success"
            }, status=status.HTTP_201_CREATED, headers=headers)
        except serializers.ValidationError as e:
            # 处理验证错误，格式化错误信息
            error_messages = self._format_error_messages(e.detail)
            return Response({
                "error": error_messages,
                "status": "error"
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # 处理其他异常
            return Response({
                "error": str(e),
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _format_error_messages(self, errors):
        """格式化错误消息"""
        if isinstance(errors, dict):
            formatted = {}
            for key, value in errors.items():
                if isinstance(value, list) and len(value) > 0:
                    # 如果是列表，选择第一个错误消息
                    formatted[key] = value[0]
                else:
                    formatted[key] = value
            return formatted
        return errors
        
    def _get_client_ip(self, request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')

# 登录视图
class LoginView(APIView):
    permission_classes = (permissions.AllowAny,)
    # 设置登录尝试限制：5次/小时
    MAX_ATTEMPTS = 5
    TIMEOUT = 60 * 60  # 1小时（单位：秒）

    def post(self, request, *args, **kwargs):
        # 检查是否已超过尝试次数
        client_ip = self._get_client_ip(request)
        cache_key = f"login_attempts_{client_ip}"
        login_attempts = cache.get(cache_key, 0)
        
        if login_attempts >= self.MAX_ATTEMPTS:
            return Response({
                "error": "登录尝试次数过多，请稍后再试",
                "lockout": True,
                "status": "error"
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
        serializer = LoginSerializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
            
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            
            user = authenticate(request, username=username, password=password)
            
            if user:
                login(request, user)
                # 登录成功后清除尝试次数
                cache.delete(cache_key)
                
                return Response({
                    "user": UserSerializer(user).data,
                    "message": "登录成功",
                    "status": "success"
                })
            else:
                # 记录失败的尝试
                cache.set(cache_key, login_attempts + 1, self.TIMEOUT)
                
                return Response({
                    "error": "用户名或密码错误",
                    "attempts_left": self.MAX_ATTEMPTS - (login_attempts + 1),
                    "status": "error"
                }, status=status.HTTP_401_UNAUTHORIZED)
                
        except serializers.ValidationError as e:
            return Response({
                "error": self._get_error_message(e),
                "status": "error"
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def _get_error_message(self, error):
        """从错误中提取消息"""
        if hasattr(error, 'detail'):
            detail = error.detail
            if isinstance(detail, dict) and 'error' in detail:
                return detail['error']
            return str(detail)
        return str(error)
        
    def _get_client_ip(self, request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')

# 登出视图
class LogoutView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        logout(request)
        return Response({
            "message": "成功退出登录",
            "status": "success"
        }, status=status.HTTP_200_OK)

# 获取当前用户信息
class UserView(generics.RetrieveAPIView):
    permission_classes = (permissions.AllowAny,)  # 允许所有用户访问
    serializer_class = UserSerializer

    def get_object(self):
        if not self.request.user.is_authenticated:
            return None
        return self.request.user
        
    def retrieve(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            # 未登录用户返回空数据，不返回403错误
            return Response({
                "user": None,
                "authenticated": False,
                "status": "success"
            })
            
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            "user": serializer.data,
            "authenticated": True,
            "status": "success"
        })

# 更新用户信息
class UpdateUserView(generics.UpdateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserUpdateSerializer
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            
            return Response({
                "user": UserSerializer(instance).data,
                "message": "用户信息更新成功",
                "status": "success"
            })
        except serializers.ValidationError as e:
            return Response({
                "error": e.detail,
                "status": "error"
            }, status=status.HTTP_400_BAD_REQUEST)

# 检查用户名是否可用
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def check_username(request):
    username = request.data.get('username', '')
    if not username:
        return Response({
            "available": False, 
            "message": "用户名不能为空",
            "status": "error"
        })
    
    exists = User.objects.filter(username=username).exists()
    return Response({
        "available": not exists,
        "message": "用户名已存在" if exists else "用户名可用",
        "status": "success" if not exists else "error"
    })

# 密码重置请求
class PasswordResetView(APIView):
    permission_classes = (permissions.AllowAny,)
    
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        if not email:
            return Response({
                "error": "请提供电子邮箱地址",
                "status": "error"
            }, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            user = User.objects.get(email=email)
            # 生成重置令牌
            from django.contrib.auth.tokens import default_token_generator
            from django.utils.http import urlsafe_base64_encode
            from django.utils.encoding import force_bytes
            
            # 生成用户ID和令牌
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            
            # 构建重置链接（前端处理）
            reset_url = f"/reset-password?uid={uid}&token={token}"
            
            # 在实际应用中，应该发送邮件
            # 这里只模拟成功响应
            return Response({
                "message": "密码重置链接已发送到您的邮箱",
                "reset_url": reset_url,  # 开发环境下返回，生产环境应该去掉
                "status": "success"
            })
        except User.DoesNotExist:
            # 出于安全考虑，不应透露用户是否存在
            return Response({
                "message": "如果该邮箱已注册，密码重置链接将发送到您的邮箱",
                "status": "success"
            })
        except Exception as e:
            return Response({
                "error": "发送重置邮件时出错",
                "status": "error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# 密码重置确认
class PasswordResetConfirmView(APIView):
    permission_classes = (permissions.AllowAny,)
    
    def post(self, request, *args, **kwargs):
        uid = request.data.get('uid')
        token = request.data.get('token')
        password = request.data.get('password')
        password2 = request.data.get('password2')
        
        # 验证请求数据
        if not uid or not token or not password or not password2:
            return Response({
                "error": "请提供所有必要的字段",
                "status": "error"
            }, status=status.HTTP_400_BAD_REQUEST)
            
        if password != password2:
            return Response({
                "error": "两次输入的密码不一致",
                "status": "error"
            }, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # 解码用户ID并获取用户
            from django.utils.http import urlsafe_base64_decode
            from django.utils.encoding import force_str
            
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
            
            # 验证令牌
            from django.contrib.auth.tokens import default_token_generator
            if not default_token_generator.check_token(user, token):
                return Response({
                    "error": "密码重置链接无效或已过期",
                    "status": "error"
                }, status=status.HTTP_400_BAD_REQUEST)
                
            # 验证密码强度
            try:
                from django.contrib.auth.password_validation import validate_password
                validate_password(password, user)
            except Exception as e:
                return Response({
                    "error": "密码不符合要求",
                    "details": list(e.messages) if hasattr(e, 'messages') else [str(e)],
                    "status": "error"
                }, status=status.HTTP_400_BAD_REQUEST)
                
            # 设置新密码
            user.set_password(password)
            user.save()
            
            return Response({
                "message": "密码重置成功，请使用新密码登录",
                "status": "success"
            })
        except Exception as e:
            return Response({
                "error": "重置密码时出错",
                "status": "error"
            }, status=status.HTTP_400_BAD_REQUEST)
