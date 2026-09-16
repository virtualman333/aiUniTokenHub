from rest_framework import serializers

from apps.utils.channel_stats import success_rate

from .upstream_models import UpstreamAccount, ModelUpstreamAccount


class UpstreamAccountSerializer(serializers.ModelSerializer):
    """上游账号序列化器"""
    
    class Meta:
        model = UpstreamAccount
        fields = [
            'id', 'name', 'provider', 'protocol', 'base_url', 'api_key', 'proxy_url',
            'max_rpm', 'max_tpm', 'is_active', 'is_available', 
            'last_error', 'order', 'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'api_key': {'write_only': True},
            'last_error': {'read_only': True},
            'is_available': {'read_only': True}
        }


class UpstreamAccountListSerializer(serializers.ModelSerializer):
    """上游账号列表序列化器

    统计口径（`total_calls` / `error_count` / `success_rate` / `last_used`）——
    这几个数字**不在 `UpstreamAccount` 上**，而在 `ModelUpstreamAccount`（模型-账号
    绑定）上，所以这里读的是视图层 `Sum` / `Max` 聚合出来的注记字段。

    为什么必须由后端算：管理页原先自己去读 `row.total_calls` / `row.success_rate`
    —— 这些键**从来不在响应里**，于是「调用次数」永远 0、「成功率」被前端写成
    `Number(row.success_rate || 0).toFixed(1)` 永远 0.0%，而同一页的汇总卡片又按
    `|| 100` 兜底显示成 100.0%。同一页两个数字互相矛盾，且都不是真的。
    `success_rate` 的分母口径只在 `apps.utils.channel_stats` 里定义一份。
    """
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    model_count = serializers.SerializerMethodField()
    # 视图层 `.annotate(...)` 提供的聚合值；直接用 IntegerField 读，避免每行再查一次库
    total_calls = serializers.IntegerField(read_only=True)
    error_count = serializers.IntegerField(read_only=True)
    last_used = serializers.DateTimeField(read_only=True)
    success_rate = serializers.SerializerMethodField()

    class Meta:
        model = UpstreamAccount
        fields = [
            'id', 'name', 'provider', 'provider_name', 'protocol', 'base_url',
            'max_rpm', 'is_active', 'is_available', 'model_count', 'order',
            # 编辑弹窗要预填的字段：列表里不给的话，弹窗会退回表单默认值
            # （max_tpm 显示成 100000、proxy_url 显示成空），
            # 一保存就等于把账号上真实的配置**静默改掉**了。
            'max_tpm', 'proxy_url',
            # 统计
            'total_calls', 'error_count', 'success_rate', 'last_used',
        ]

    def get_model_count(self, obj):
        return obj.model_bindings.filter(is_enabled=True).count()

    def get_success_rate(self, obj):
        return success_rate(getattr(obj, 'total_calls', 0), getattr(obj, 'error_count', 0))


class ModelUpstreamAccountSerializer(serializers.ModelSerializer):
    """模型账号关联序列化器"""
    account_name = serializers.CharField(source='account.name', read_only=True)
    account_url = serializers.CharField(source='account.base_url', read_only=True)
    account_active = serializers.BooleanField(source='account.is_active', read_only=True)
    cost_input_price = serializers.FloatField()
    cost_output_price = serializers.FloatField()
    cost_cached_input_price = serializers.FloatField()

    class Meta:
        model = ModelUpstreamAccount
        fields = [
            'id', 'model', 'account', 'account_name', 'account_url',
            'account_active', 'weight', 'is_enabled',
            'cost_input_price', 'cost_output_price', 'cost_cached_input_price',
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
