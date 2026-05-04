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
        return Response({
            'message': '注册成功',
            'user': UserSerializer(user).data,
            'token': token
        }, status=status.HTTP_201_CREATED)
    
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
            return Response({'message': '用户名或密码错误'}, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.is_active:
            return Response({'message': '账号已被禁用'}, status=status.HTTP_401_UNAUTHORIZED)
        
        token = generate_token(user)
        return Response({
            'message': '登录成功',
            'user': UserSerializer(user).data,
            'token': token
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """获取当前用户信息"""
        return Response(UserSerializer(request.user).data)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """修改密码"""
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return Response({'message': '密码修改成功'})


class APIKeyViewSet(viewsets.ModelViewSet):
    """API密钥管理"""
    serializer_class = APIKeySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return APIKey.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['delete'])
    def revoke(self, request):
        """撤销密钥"""
        key_id = request.data.get('key_id')
        try:
            api_key = self.get_queryset().get(id=key_id)
            api_key.delete()
            return Response({'message': '密钥已撤销'})
        except APIKey.DoesNotExist:
            return Response({'message': '密钥不存在'}, status=status.HTTP_404_NOT_FOUND)
