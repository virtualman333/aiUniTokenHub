from rest_framework import serializers
from .upstream_models import UpstreamAccount, ModelUpstreamAccount


class UpstreamAccountSerializer(serializers.ModelSerializer):
    """上游账号序列化器"""
    
    class Meta:
        model = UpstreamAccount
        fields = [
            'id', 'name', 'provider', 'base_url', 'api_key', 'proxy_url',
            'max_rpm', 'max_tpm', 'is_active', 'is_available', 
            'last_error', 'order', 'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'api_key': {'write_only': True},
            'last_error': {'read_only': True},
            'is_available': {'read_only': True}
        }


class UpstreamAccountListSerializer(serializers.ModelSerializer):
    """上游账号列表序列化器"""
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    model_count = serializers.SerializerMethodField()
    
    class Meta:
        model = UpstreamAccount
        fields = [
            'id', 'name', 'provider', 'provider_name', 'base_url', 
            'max_rpm', 'is_active', 'is_available', 'model_count', 'order'
        ]
    
    def get_model_count(self, obj):
        return obj.model_bindings.filter(is_enabled=True).count()


class ModelUpstreamAccountSerializer(serializers.ModelSerializer):
    """模型账号关联序列化器"""
    account_name = serializers.CharField(source='account.name', read_only=True)
    account_url = serializers.CharField(source='account.base_url', read_only=True)
    account_active = serializers.BooleanField(source='account.is_active', read_only=True)
    
    class Meta:
        model = ModelUpstreamAccount
        fields = [
            'id', 'model', 'account', 'account_name', 'account_url', 
            'account_active', 'weight', 'is_enabled',
            'usage_count', 'error_count', 'last_used', 'created_at'
        ]
        read_only_fields = ['usage_count', 'error_count', 'last_used']


class ModelUpstreamAccountCreateSerializer(serializers.Serializer):
    """批量添加模型账号"""
    account_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text='上游账号ID列表'
    )
    weight = serializers.IntegerField(default=1, min_value=1, max_value=100)
