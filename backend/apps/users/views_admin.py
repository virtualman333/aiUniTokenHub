from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate
from apps.users.models import User, APIKey
from .serializers import (
    UserRegisterSerializer, UserLoginSerializer, UserSerializer,
    APIKeySerializer, ChangePasswordSerializer, AdminUserSerializer
)


class AdminUserViewSet(viewsets.ModelViewSet):
    """管理员用户管理视图"""
    queryset = User.objects.all().order_by('-created_at')
    serializer_class = AdminUserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # 过滤参数
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(username__icontains=search)
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        return queryset
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def toggle_status(self, request, pk=None):
        """切换用户状态"""
        user = self.get_object()
        user.is_active = not user.is_active
        user.save()
        return Response({
            'message': f'用户已{"启用" if user.is_active else "禁用"}',
            'is_active': user.is_active
        })
    
    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """重置用户密码"""
        user = self.get_object()
        new_password = request.data.get('password', '123456')
        user.set_password(new_password)
        user.save()
        return Response({
            'message': f'密码已重置为: {new_password}'
        })
    
    @action(detail=True, methods=['post'])
    def adjust_balance(self, request, pk=None):
        """调整用户余额"""
        user = self.get_object()
        amount = request.data.get('amount', 0)
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return Response({'message': '无效的金额'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.balance += amount
        if user.balance < 0:
            return Response({'message': '余额不足'}, status=status.HTTP_400_BAD_REQUEST)
        user.save()
        
        return Response({
            'message': f'余额调整成功',
            'balance': user.balance
        })
