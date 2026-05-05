from rest_framework import serializers
from .models import APIAccessLog


class APIAccessLogSerializer(serializers.ModelSerializer):
    """访问日志序列化器"""
    username = serializers.CharField(source='user.username', read_only=True, default='匿名')
    user_role = serializers.CharField(source='user.role', read_only=True, default='')
    api_key_name = serializers.CharField(source='api_key.name', read_only=True, default='')
    api_key_key = serializers.CharField(source='api_key.key', read_only=True, default='')
    
    class Meta:
        model = APIAccessLog
        fields = [
            'id', 'username', 'user_role',
            'api_key', 'api_key_name', 'api_key_key',
            'method', 'path', 'request_headers', 'request_params', 'request_body',
            'response_status', 'response_body', 'response_time',
            'ip_address', 'error_message', 'created_at'
        ]


class AccessLogStatSerializer(serializers.Serializer):
    """访问统计序列化器"""
    date = serializers.DateField()
    total_count = serializers.IntegerField()
    success_count = serializers.IntegerField()
    error_count = serializers.IntegerField()
    avg_response_time = serializers.FloatField()


class ProxyRequestSerializer(serializers.Serializer):
    method = serializers.ChoiceField(
        choices=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
        required=False
    )
    headers = serializers.DictField(required=False, default=dict)
    params = serializers.DictField(required=False, default=dict)
    data = serializers.JSONField(required=False)
