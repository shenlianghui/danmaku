from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core import exceptions

# 用户序列化器
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'date_joined')
        read_only_fields = ('date_joined',)

# 注册序列化器
class RegisterSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(write_only=True, required=True)
    email = serializers.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'password2', 'first_name', 'last_name')
        extra_kwargs = {
            'password': {'write_only': True},
            'first_name': {'required': False},
            'last_name': {'required': False}
        }

    def validate_email(self, value):
        """验证邮箱唯一性"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("该邮箱已被注册")
        return value
        
    def validate_username(self, value):
        """额外的用户名验证"""
        if len(value) < 3:
            raise serializers.ValidationError("用户名长度至少为3个字符")
        if not value.isalnum():
            raise serializers.ValidationError("用户名只能包含字母和数字")
        return value

    def validate(self, data):
        # 检查两次密码是否一致
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "两次输入的密码不一致"})
        
        # 验证密码强度
        password = data.get('password')
        user = User(
            username=data.get('username'),
            email=data.get('email')
        )
        
        # 自定义密码验证
        password_errors = []
        
        # 检查密码长度
        if len(password) < 8:
            password_errors.append("密码长度至少为8个字符")
            
        # 检查密码是否包含数字
        if not any(char.isdigit() for char in password):
            password_errors.append("密码必须包含至少一个数字")
            
        # 检查密码是否包含字母
        if not any(char.isalpha() for char in password):
            password_errors.append("密码必须包含至少一个字母")
            
        # 检查密码是否包含特殊字符
        special_chars = set("!@#$%^&*()_+-=[]{}|;:,.<>?/")
        if not any(char in special_chars for char in password):
            password_errors.append("密码必须包含至少一个特殊字符")
            
        # 如果有自定义密码错误，则抛出
        if password_errors:
            raise serializers.ValidationError({"password": password_errors})
        
        # 如果通过了自定义验证，还要进行Django的默认验证
        try:
            validate_password(password, user)
        except exceptions.ValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
            
        return data

    def create(self, validated_data):
        validated_data.pop('password2')  # 移除确认密码字段
        
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        
        return user

# 登录序列化器
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    remember_me = serializers.BooleanField(required=False, default=False)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            raise serializers.ValidationError({"error": "请提供用户名和密码"})
        
        # 检查用户是否存在
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise serializers.ValidationError({"error": "用户名或密码错误"})
            
        # 检查账号是否被禁用
        if not user.is_active:
            raise serializers.ValidationError({"error": "用户账号已被禁用"})
            
        # 验证密码（但不在这里进行登录）
        if not authenticate(username=username, password=password):
            raise serializers.ValidationError({"error": "用户名或密码错误"})
            
        return data

# 用户资料更新序列化器
class UserUpdateSerializer(serializers.ModelSerializer):
    current_password = serializers.CharField(write_only=True, required=False)
    new_password = serializers.CharField(write_only=True, required=False)
    new_password2 = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'current_password', 'new_password', 'new_password2')
        
    def validate_email(self, value):
        """验证新邮箱是否已被使用"""
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("该邮箱已被其他账号使用")
        return value
        
    def validate(self, data):
        # 如果提供了当前密码，则进行密码更新验证
        if 'current_password' in data:
            if not self.context['request'].user.check_password(data['current_password']):
                raise serializers.ValidationError({"current_password": "当前密码不正确"})
                
            # 如果要更改密码，需要验证新密码
            if 'new_password' in data:
                if 'new_password2' not in data:
                    raise serializers.ValidationError({"new_password2": "请提供确认密码"})
                if data['new_password'] != data['new_password2']:
                    raise serializers.ValidationError({"new_password": "两次输入的新密码不一致"})
                    
                # 验证新密码强度
                try:
                    validate_password(data['new_password'], self.context['request'].user)
                except exceptions.ValidationError as e:
                    raise serializers.ValidationError({"new_password": list(e.messages)})
            elif 'new_password2' in data:
                raise serializers.ValidationError({"new_password": "请提供新密码"})
        
        # 如果只提供了新密码字段，但没有当前密码，则报错
        elif 'new_password' in data or 'new_password2' in data:
            raise serializers.ValidationError({"current_password": "更改密码需要提供当前密码"})
            
        return data
        
    def update(self, instance, validated_data):
        # 移除密码相关字段
        current_password = validated_data.pop('current_password', None)
        new_password = validated_data.pop('new_password', None)
        validated_data.pop('new_password2', None)
        
        # 更新其他字段
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            
        # 如果提供了新密码，则更新密码
        if current_password and new_password:
            instance.set_password(new_password)
            
        instance.save()
        return instance 