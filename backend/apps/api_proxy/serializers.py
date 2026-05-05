from rest_framework import serializers
from .models import APIAccessLog


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
