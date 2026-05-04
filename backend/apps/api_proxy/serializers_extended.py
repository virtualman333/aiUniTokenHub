"""
扩展的序列化器
"""
from rest_framework import serializers
from apps.api_proxy.models import APIEndpoint, APIAccessLog


class APIEndpointDetailSerializer(serializers.ModelSerializer):
    """API端点详情序列化器（包含更多信息）"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    usage_count = serializers.SerializerMethodField()
    
    class Meta:
        model = APIEndpoint
        fields = '__all__'
    
    def get_usage_count(self, obj):
        return obj.access_logs.count()


class APIAccessLogSerializer(serializers.ModelSerializer):
    """API访问日志序列化器"""
    endpoint_name = serializers.CharField(source='endpoint.name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = APIAccessLog
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class ProxyResponseSerializer(serializers.Serializer):
    """代理响应序列化器"""
    success = serializers.BooleanField()
    data = serializers.JSONField()
    status = serializers.IntegerField()
    response_time = serializers.IntegerField()
