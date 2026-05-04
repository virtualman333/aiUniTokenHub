"""
API密钥管理视图（用户侧）
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
import secrets

from apps.users.models import APIKey
from apps.users.serializers import APIKeySerializer


class UserAPIKeyViewSet(viewsets.ModelViewSet):
    """
    用户API密钥管理
    用户可以查看、创建、删除自己的API Key
    """
    serializer_class = APIKeySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """只返回当前用户的API Key"""
        return APIKey.objects.filter(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """创建新的API Key"""
        name = request.data.get('name', f"Key-{timezone.now().strftime('%Y%m%d%H%M')}")
        
        # 生成密钥
        key = f"utk_{secrets.token_urlsafe(32)}"
        
        api_key = APIKey.objects.create(
            user=request.user,
            name=name,
            key=key,
            is_active=True,
        )
        
        return Response({
            'id': api_key.id,
            'name': api_key.name,
            'key': key,  # 只在创建时返回完整密钥
            'created_at': api_key.created_at,
            'message': '请妥善保存密钥，只显示一次！'
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """吊销API Key"""
        api_key = self.get_object()
        api_key.is_active = False
        api_key.save()
        return Response({'message': 'API Key已吊销'})
    
    @action(detail=False, methods=['get'])
    def usage(self, request):
        """获取API Key使用统计"""
        from apps.api_proxy.models import APIAccessLog
        
        queryset = APIAccessLog.objects.filter(api_key__user=request.user)
        
        # 按API端点统计
        from django.db.models import Count, Avg
        stats = queryset.values('endpoint__name').annotate(
            total_calls=Count('id'),
            avg_response_time=Avg('response_time')
        ).order_by('-total_calls')
        
        return Response({
            'total_calls': queryset.count(),
            'by_endpoint': list(stats),
            'recent_logs': APIAccessLogSerializer(
                queryset.order_by('-created_at')[:10],
                many=True
            ).data
        })


class APIAccessLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API访问日志（用户侧）
    """
    serializer_class = APIAccessLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return APIAccessLog.objects.filter(user=self.request.user)
