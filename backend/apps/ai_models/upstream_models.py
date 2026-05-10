from django.db import models
from apps.ai_models.models import AIModel, ModelProvider


class UpstreamAccount(models.Model):
    """上游账号池"""
    
    name = models.CharField('账号名称', max_length=100)
    provider = models.ForeignKey(ModelProvider, on_delete=models.CASCADE, 
                                 related_name='upstream_accounts', verbose_name='供应商')
    
    # API配置
    PROTOCOL_CHOICES = [
        ('openai', 'OpenAI兼容'),
        ('anthropic', 'Anthropic'),
        ('gemini', 'Gemini'),
    ]
    protocol = models.CharField('协议', max_length=20, choices=PROTOCOL_CHOICES, default='openai')
    base_url = models.CharField('API基础地址', max_length=500, 
                                help_text='如: https://api.openai.com/v1')
    api_key = models.CharField('API密钥', max_length=500)
    
    # 可选代理配置
    proxy_url = models.CharField('代理地址', max_length=500, blank=True,
                                 help_text='留空则直连')
    
    # 限流配置
    max_rpm = models.IntegerField('最大请求速率(次/分钟)', default=60)
    max_tpm = models.IntegerField('最大Token速率(次/分钟)', default=100000)
    
    # 状态
    is_active = models.BooleanField('是否启用', default=True)
    is_available = models.BooleanField('是否可用', default=True,
                                       help_text='自动检测，宕机时自动标记')
    last_error = models.TextField('最近错误', blank=True)
    
    order = models.IntegerField('排序', default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'upstream_accounts'
        verbose_name = '上游账号'
        verbose_name_plural = '上游账号'
        ordering = ['-is_active', 'order', 'id']
    
    def __str__(self):
        return f"{self.name} ({self.provider.name})"


class ModelUpstreamAccount(models.Model):
    """模型与上游账号关联"""
    
    model = models.ForeignKey(AIModel, on_delete=models.CASCADE,
                              related_name='upstream_accounts', verbose_name='模型')
    account = models.ForeignKey(UpstreamAccount, on_delete=models.CASCADE,
                                 related_name='model_bindings', verbose_name='上游账号')
    
    # 负载均衡配置
    weight = models.IntegerField('权重', default=1,
                                  help_text='权重越高，被选中的概率越大')
    is_enabled = models.BooleanField('是否启用', default=True)
    
    # 统计
    usage_count = models.IntegerField('使用次数', default=0)
    error_count = models.IntegerField('错误次数', default=0)
    last_used = models.DateTimeField('上次使用', null=True, blank=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        db_table = 'model_upstream_accounts'
        verbose_name = '模型账号关联'
        verbose_name_plural = '模型账号关联'
        unique_together = ['model', 'account']
    
    def __str__(self):
        return f"{self.model.name} -> {self.account.name}"
