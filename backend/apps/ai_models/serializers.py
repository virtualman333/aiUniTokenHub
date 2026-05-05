from rest_framework import serializers
from .models import AIModel, ModelProvider, ModelCategory


class ModelProviderSerializer(serializers.ModelSerializer):
    """供应商序列化器"""
    model_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ModelProvider
        fields = ['id', 'name', 'code', 'logo', 'description', 'is_active', 'model_count']
    
    def get_model_count(self, obj):
        return obj.models.filter(status='active').count()


class ModelCategorySerializer(serializers.ModelSerializer):
    """分类序列化器"""
    model_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ModelCategory
        fields = ['id', 'name', 'code', 'icon', 'is_active', 'model_count']
    
    def get_model_count(self, obj):
        return obj.models.filter(status='active').count()


class AIModelListSerializer(serializers.ModelSerializer):
    """模型列表序列化器"""
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    provider_code = serializers.CharField(source='provider.code', read_only=True)
    provider_logo = serializers.CharField(source='provider.logo', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    # 使用 _account_count 来判断 has_accounts
    account_count = serializers.IntegerField(source='_account_count', default=0)
    has_accounts = serializers.SerializerMethodField()
    
    def get_has_accounts(self, obj):
        return getattr(obj, '_account_count', 0) > 0
    
    class Meta:
        model = AIModel
        fields = [
            'id', 'name', 'code', 'version', 'provider_name', 'provider_code', 'provider_logo',
            'category_name', 'input_price', 'output_price', 'description',
            'supports_streaming', 'supports_vision', 'supports_tools', 'supports_json',
            'context_window', 'max_tokens', 'capabilities', 'tags',
            'status', 'is_featured', 'is_new', 'usage_count', 'rating',
            'has_accounts', 'account_count', 'created_at'
        ]


class AIModelDetailSerializer(serializers.ModelSerializer):
    """模型详情序列化器"""
    provider = ModelProviderSerializer(read_only=True)
    category = ModelCategorySerializer(read_only=True)
    
    class Meta:
        model = AIModel
        fields = '__all__'


class AIModelCreateSerializer(serializers.ModelSerializer):
    """模型创建/更新序列化器"""
    
    class Meta:
        model = AIModel
        fields = '__all__'
        read_only_fields = ['usage_count', 'rating', 'created_at', 'updated_at']
