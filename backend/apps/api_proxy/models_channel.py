"""
上游渠道模型
支持多渠道负载均衡和故障转移
"""
from django.db import models
from apps.ai_models.models import AIModel, ModelProvider


class APIChannel(models.Model):
    """
    API上游渠道
    用于配置多个上游供应商，支持负载均衡
    """
    name = models.CharField('渠道名称', max_length=100)
    provider = models.ForeignKey(
        ModelProvider, 
        on_delete=models.CASCADE,
        related_name='channels',
        verbose_name='模型供应商'
    )
    base_url = models.URLField('基础URL', max_length=500)
    api_key = models.CharField('API Key', max_length=500, blank=True)
    api_secret = models.CharField('API Secret', max_length=500, blank=True)
    
    # 负载均衡配置
    WEIGHT_CHOICES = [
        (1, '低权重 (1)'),
        (2, '中权重 (2)'),
        (3, '高权重 (3)'),
    ]
    weight = models.IntegerField('权重', default=1, choices=WEIGHT_CHOICES)
    
    # 状态控制
    STATUS_CHOICES = [
        ('active', '正常'),
        ('disabled', '已禁用'),
        ('maintenance', '维护中'),
        ('error', '异常'),
    ]
    status = models.CharField('状态', max_length=20, default='active', choices=STATUS_CHOICES)
    
    # 限流配置
    max_qps = models.IntegerField('最大QPS', default=100)
    max_tpm = models.IntegerField('最大TPM(每分钟)', default=100000)
    timeout = models.IntegerField('超时时间(秒)', default=120)
    
    # 统计
    total_calls = models.BigIntegerField('总调用次数', default=0)
    success_rate = models.FloatField('成功率', default=100.0)
    avg_latency = models.IntegerField('平均延迟(ms)', default=0)
    
    # 额度控制
    remaining_quota = models.BigIntegerField('剩余配额', null=True, blank=True,
                                            help_text='null表示无限制')
    
    # 优先级（数字越小优先级越高）
    priority = models.IntegerField('优先级', default=100)
    
    is_default = models.BooleanField('默认渠道', default=False)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = 'API渠道'
        verbose_name_plural = 'API渠道'
        ordering = ['priority', '-weight']
    
    def __str__(self):
        return f"{self.name} ({self.provider.name})"
    
    def increment_calls(self, success=True, latency=0):
        """增加调用计数"""
        self.total_calls += 1
        if success:
            # 更新成功率（简化计算）
            self.success_rate = min(100, self.success_rate + 0.01)
        else:
            self.success_rate = max(0, self.success_rate - 0.1)
        # 更新平均延迟
        if self.total_calls > 1:
            self.avg_latency = int(
                (self.avg_latency * (self.total_calls - 1) + latency) / self.total_calls
            )
        self.save(update_fields=['total_calls', 'success_rate', 'avg_latency'])


class ChannelHealthLog(models.Model):
    """渠道健康检查日志"""
    channel = models.ForeignKey(APIChannel, on_delete=models.CASCADE, related_name='health_logs')
    status_code = models.IntegerField('状态码')
    response_time = models.IntegerField('响应时间(ms)')
    is_success = models.BooleanField('是否成功')
    error_message = models.TextField('错误信息', blank=True)
    created_at = models.DateTimeField('检查时间', auto_now_add=True)
    
    class Meta:
        verbose_name = '渠道健康日志'
        verbose_name_plural = '渠道健康日志'
        ordering = ['-created_at']


class ModelChannelBinding(models.Model):
    """
    模型与渠道的绑定关系
    定义某个模型使用哪些渠道
    """
    model = models.ForeignKey(AIModel, on_delete=models.CASCADE, related_name='channel_bindings')
    channel = models.ForeignKey(APIChannel, on_delete=models.CASCADE, related_name='model_bindings')
    is_active = models.BooleanField('启用', default=True)
    priority = models.IntegerField('优先级', default=100)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        verbose_name = '模型渠道绑定'
        verbose_name_plural = '模型渠道绑定'
        ordering = ['priority']
    
    def __str__(self):
        return f"{self.model.name} -> {self.channel.name}"
