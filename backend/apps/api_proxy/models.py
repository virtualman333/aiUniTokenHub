from django.db import models
from apps.users.models import User, APIKey
from apps.ai_models.models import AIModel
from apps.ai_models.upstream_models import UpstreamAccount


class APIAccessLog(models.Model):
    """API访问记录"""
    api_key = models.ForeignKey(APIKey, on_delete=models.SET_NULL, null=True, related_name='access_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='access_logs')
    
    # 新增：模型和上游账号信息
    model = models.ForeignKey(AIModel, on_delete=models.SET_NULL, null=True, blank=True,
                            related_name='access_logs', verbose_name='模型')
    upstream_account = models.ForeignKey(UpstreamAccount, on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='access_logs', verbose_name='上游账号')
    
    method = models.CharField('方法', max_length=10)
    path = models.CharField('路径', max_length=500)
    request_headers = models.JSONField('请求头', default=dict)
    request_params = models.JSONField('请求参数', default=dict)
    request_body = models.TextField('请求体', blank=True)
    response_status = models.IntegerField('响应状态', default=0)
    response_body = models.TextField('响应体', blank=True)
    response_time = models.IntegerField('响应时间(ms)', default=0)
    ip_address = models.GenericIPAddressField('IP地址', null=True, blank=True)
    error_message = models.TextField('错误信息', blank=True)

    # Token 用量与费用
    input_tokens = models.IntegerField('输入Token', default=0)
    output_tokens = models.IntegerField('输出Token', default=0)
    total_tokens = models.IntegerField('总Token', default=0)
    cached_tokens = models.IntegerField('缓存命中Token', default=0)
    cost = models.DecimalField('费用(元)', max_digits=12, decimal_places=6, default=0)

    created_at = models.DateTimeField('访问时间', auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'api_access_logs'
        verbose_name = 'API访问记录'
        verbose_name_plural = 'API访问记录'
        ordering = ['-created_at']


class Conversation(models.Model):
    """AI 对话会话"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations', verbose_name='用户')
    title = models.CharField('标题', max_length=200, default='新对话')
    model_code = models.CharField('使用模型', max_length=128, blank=True, default='')
    system_prompt = models.TextField('系统提示', blank=True, default='')
    is_pinned = models.BooleanField('置顶', default=False)
    last_message_at = models.DateTimeField('最近消息时间', auto_now=True, db_index=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'chat_conversations'
        verbose_name = 'AI对话会话'
        verbose_name_plural = 'AI对话会话'
        ordering = ['-is_pinned', '-last_message_at']

    def __str__(self):
        return f'{self.title} ({self.user_id})'


class ChatMessage(models.Model):
    """AI 对话消息"""
    ROLE_CHOICES = (
        ('system', 'system'),
        ('user', 'user'),
        ('assistant', 'assistant'),
    )

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE,
                                     related_name='messages', verbose_name='会话')
    role = models.CharField('角色', max_length=16, choices=ROLE_CHOICES)
    content = models.TextField('内容', blank=True, default='')
    model_code = models.CharField('模型', max_length=128, blank=True, default='')
    prompt_tokens = models.IntegerField('提示tokens', default=0)
    completion_tokens = models.IntegerField('回复tokens', default=0)
    total_tokens = models.IntegerField('总tokens', default=0)
    usage_details = models.JSONField('用量明细', default=dict, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'chat_messages'
        verbose_name = 'AI对话消息'
        verbose_name_plural = 'AI对话消息'
        ordering = ['created_at', 'id']

    def __str__(self):
        return f'[{self.role}] {self.content[:30]}'
