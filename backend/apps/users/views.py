from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate
from .models import User, APIKey
from .serializers import (
    UserRegisterSerializer, UserLoginSerializer, UserSerializer,
    APIKeySerializer, ChangePasswordSerializer
)
from .authentication import generate_token
from apps.utils.response import APIResponse


class AuthViewSet(viewsets.GenericViewSet):
    """认证视图集"""
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def register(self, request):
        """用户注册"""
        serializer = UserRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token = generate_token(user)
        return APIResponse.created({
            'user': UserSerializer(user).data,
            'token': token
        }, '注册成功')
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        """用户登录"""
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password']
        )
        
        if not user:
            return APIResponse.error('用户名或密码错误', 401)
        
        if not user.is_active:
            return APIResponse.error('账号已被禁用', 401)
        
        token = generate_token(user)
        return APIResponse.success({
            'user': UserSerializer(user).data,
            'token': token
        }, '登录成功')
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """获取当前用户信息"""
        return APIResponse.success(UserSerializer(request.user).data, '获取成功')
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """修改密码"""
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return APIResponse.success(None, '密码修改成功')


class APIKeyViewSet(viewsets.ModelViewSet):
    """API密钥管理"""
    serializer_class = APIKeySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return APIKey.objects.filter(user=self.request.user)
    
    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return APIResponse.success(serializer.data, '获取成功')
    
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return APIResponse.created(serializer.data, '创建成功')
    
    def destroy(self, request, pk=None):
        instance = self.get_object()
        instance.delete()
        return APIResponse.success(None, '删除成功')
    
    @action(detail=False, methods=['delete'])
    def revoke(self, request):
        """撤销密钥"""
        key_id = request.data.get('key_id')
        try:
            api_key = self.get_queryset().get(id=key_id)
            api_key.delete()
            return APIResponse.success(None, '密钥已撤销')
        except APIKey.DoesNotExist:
            return APIResponse.error('密钥不存在', 404)
