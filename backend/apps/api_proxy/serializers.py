from rest_framework import serializers
from .models import APICategory, APIEndpoint, APIAccessLog


class APICategorySerializer(serializers.ModelSerializer):
    endpoint_count = serializers.SerializerMethodField()
    
    class Meta:
        model = APICategory
        fields = ['id', 'name', 'description', 'icon', 'order', 'endpoint_count']
    
    def get_endpoint_count(self, obj):
        return obj.endpoints.filter(is_active=True).count()


class APIEndpointSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = APIEndpoint
        fields = ['id', 'category', 'category_name', 'name', 'path', 'method',
                   'description', 'doc_url', 'is_public', 'rate_limit', 'price',
                   'timeout', 'created_at']


class ProxyRequestSerializer(serializers.Serializer):
    method = serializers.ChoiceField(
        choices=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
        required=False
    )
    headers = serializers.DictField(required=False, default=dict)
    params = serializers.DictField(required=False, default=dict)
    data = serializers.JSONField(required=False)


class APIAccessLogSerializer(serializers.ModelSerializer):
    endpoint_name = serializers.CharField(source='endpoint.name', read_only=True)
    api_key_name = serializers.CharField(source='api_key.name', read_only=True)
    
    class Meta:
        model = APIAccessLog
        fields = ['id', 'api_key', 'api_key_name', 'endpoint', 'endpoint_name',
                   'method', 'path', 'response_status', 'response_time',
                   'ip_address', 'created_at']
