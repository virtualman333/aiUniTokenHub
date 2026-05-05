from rest_framework import serializers
from .models import APICategory, APIEndpoint, APIAccessLog


class APICategorySerializer(serializers.ModelSerializer):
    endpoint_count = serializers.SerializerMethodField()
    
    class Meta:
        model = APICategory
        fields = ['id', 'name', 'description', 'icon', 'order', 'is_active', 'endpoint_count']
    
    def get_endpoint_count(self, obj):
        return obj.endpoints.filter(is_active=True).count()


class APIEndpointSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    price = serializers.SerializerMethodField()
    
    class Meta:
        model = APIEndpoint
        fields = [
            'id', 'category', 'category_name', 'name', 'path', 'method',
            'description', 'doc_url', 'target_url', 'headers', 'parameters',
            'is_public', 'is_active', 'rate_limit', 'price', 'timeout',
            'created_at', 'updated_at'
        ]
    
    def get_price(self, obj):
        """确保price返回浮点数而非Decimal"""
        return float(obj.price) if obj.price else 0.0


class APIAccessLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True, default='匿名')
    endpoint_name = serializers.CharField(source='endpoint.name', read_only=True, default='')
    
    class Meta:
        model = APIAccessLog
        fields = [
            'id', 'username', 'api_key', 'endpoint', 'endpoint_name',
            'method', 'path', 'request_headers', 'request_params', 'request_body',
            'response_status', 'response_body', 'response_time',
            'ip_address', 'error_message', 'created_at'
        ]


class ProxyRequestSerializer(serializers.Serializer):
    method = serializers.ChoiceField(
        choices=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
        required=False
    )
    headers = serializers.DictField(required=False, default=dict)
    params = serializers.DictField(required=False, default=dict)
    data = serializers.JSONField(required=False)
