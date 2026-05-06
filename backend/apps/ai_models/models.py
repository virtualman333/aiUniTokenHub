from django.db import models


class ModelProvider(models.Model):
    """模型供应商"""
    name = models.CharField('供应商名称', max_length=100)
    code = models.CharField('供应商代码', max_length=50, unique=True)
    logo = models.URLField('Logo', blank=True)
    website = models.URLField('官网', blank=True)
    description = models.TextField('描述', blank=True)
    is_active = models.BooleanField('是否启用', default=True)
    order = models.IntegerField('排序', default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        db_table = 'model_providers'
        verbose_name = '模型供应商'
        verbose_name_plural = '模型供应商'
        ordering = ['order', 'id']
    
    def __str__(self):
        return self.name


class ModelCategory(models.Model):
    """模型分类"""
    name = models.CharField('分类名称', max_length=100)
    code = models.CharField('分类代码', max_length=50, unique=True)
    icon = models.CharField('图标', max_length=50, blank=True)
    is_active = models.BooleanField('是否启用', default=True)
    order = models.IntegerField('排序', default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        db_table = 'model_categories'
        verbose_name = '模型分类'
        verbose_name_plural = '模型分类'
        ordering = ['order', 'id']
    
    def __str__(self):
        return self.name


class AIModel(models.Model):
    """AI模型"""
    
    STATUS_CHOICES = [
        ('active', '已上架'),
        ('inactive', '已下架'),
        ('beta', '测试中'),
    ]
    
    provider = models.ForeignKey(ModelProvider, on_delete=models.CASCADE, 
                                  related_name='models', verbose_name='供应商')
    category = models.ForeignKey(ModelCategory, on_delete=models.SET_NULL, 
                                  null=True, blank=True, related_name='models', 
                                  verbose_name='分类')
    
    name = models.CharField('模型名称', max_length=200)
    code = models.CharField('模型代码', max_length=100)
    version = models.CharField('版本', max_length=50, blank=True)
    
    # 定价（单位：元 / 百万 tokens）
    input_price = models.DecimalField('输入价格(元/百万tokens)', max_digits=12, decimal_places=4, default=0)
    output_price = models.DecimalField('输出价格(元/百万tokens)', max_digits=12, decimal_places=4, default=0)
    cached_input_price = models.DecimalField(
        '缓存命中价格(元/百万tokens)', max_digits=12, decimal_places=4, default=0,
        help_text='输入 tokens 中命中缓存部分的单价；为 0 时按 input_price 计费'
    )
    
    # 功能特性
    supports_streaming = models.BooleanField('支持流式', default=True)
    supports_vision = models.BooleanField('支持视觉', default=False)
    supports_tools = models.BooleanField('支持工具调用', default=False)
    supports_json = models.BooleanField('支持JSON模式', default=False)
    context_window = models.IntegerField('上下文窗口', default=4096)
    max_tokens = models.IntegerField('最大输出tokens', default=2048)
    
    # 描述信息
    description = models.TextField('模型描述', blank=True)
    capabilities = models.JSONField('能力标签', default=list, blank=True)
    tags = models.JSONField('标签', default=list, blank=True)
    
    # 状态
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='active')
    is_featured = models.BooleanField('是否推荐', default=False)
    is_new = models.BooleanField('是否新品', default=False)
    
    # 统计
    usage_count = models.IntegerField('使用次数', default=0)
    rating = models.DecimalField('评分', max_digits=3, decimal_places=2, default=5.0)
    
    # API配置
    api_endpoint = models.CharField('API端点', max_length=500, blank=True)
    api_model_id = models.CharField('API模型ID', max_length=200, blank=True)
    
    order = models.IntegerField('排序', default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'ai_models'
        verbose_name = 'AI模型'
        verbose_name_plural = 'AI模型'
        ordering = ['-is_featured', 'order', '-created_at']
        unique_together = ['provider', 'code']
    
    def __str__(self):
        return f"{self.name} ({self.provider.name})"
