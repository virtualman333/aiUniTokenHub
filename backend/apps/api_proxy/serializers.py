from rest_framework import serializers
from .models import APIAccessLog


class APIAccessLogSerializer(serializers.ModelSerializer):
    """接口使用记录序列化器"""
    username = serializers.CharField(source='user.username', read_only=True, default='匿名')
    user_role = serializers.CharField(source='user.role', read_only=True, default='')
    api_key_name = serializers.CharField(source='api_key.name', read_only=True, default='')
    api_key_key = serializers.CharField(source='api_key.key', read_only=True, default='')
    
    # 模型信息
    model_name = serializers.CharField(source='model.name', read_only=True, default='')
    model_code = serializers.CharField(source='model.code', read_only=True, default='')
    
    # 上游账号信息
    upstream_account_name = serializers.CharField(source='upstream_account.name', read_only=True, default='')
    upstream_provider = serializers.CharField(source='upstream_account.provider.name', read_only=True, default='')

    cost = serializers.FloatField(read_only=True)
    upstream_cost = serializers.FloatField(read_only=True)
    profit = serializers.FloatField(read_only=True)
    # 前端Dashboard表格期望 status 字段（别名到 response_status）
    status = serializers.IntegerField(source='response_status', read_only=True)

    class Meta:
        model = APIAccessLog
        fields = [
            'id', 'username', 'user_role',
            'api_key', 'api_key_name', 'api_key_key',
            'model', 'model_name', 'model_code',
            'upstream_account', 'upstream_account_name', 'upstream_provider',
            'method', 'path', 'request_headers', 'request_params', 'request_body',
            'response_status', 'status', 'response_body', 'response_time',
            'input_tokens', 'output_tokens', 'total_tokens', 'cached_tokens',
            'cost', 'upstream_cost', 'profit',
            'ip_address', 'error_message', 'created_at'
        ]


class AccessLogStatSerializer(serializers.Serializer):
    """接口使用统计序列化器"""
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
