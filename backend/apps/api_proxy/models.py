from django.db import models
from apps.users.models import User, APIKey


class APICategory(models.Model):
    """API分类"""
    name = models.CharField('分类名称', max_length=100)
    description = models.TextField('分类描述', blank=True)
    icon = models.CharField('图标', max_length=50, blank=True)
    order = models.IntegerField('排序', default=0)
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        db_table = 'api_categories'
        verbose_name = 'API分类'
        verbose_name_plural = 'API分类'
        ordering = ['order']
    
    def __str__(self):
        return self.name


class APIEndpoint(models.Model):
    """API端点"""
    
    METHOD_CHOICES = [
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('DELETE', 'DELETE'),
        ('PATCH', 'PATCH'),
    ]
    
    category = models.ForeignKey(APICategory, on_delete=models.CASCADE, related_name='endpoints')
    name = models.CharField('API名称', max_length=200)
    path = models.CharField('请求路径', max_length=500)
    method = models.CharField('请求方法', max_length=10, choices=METHOD_CHOICES, default='GET')
    description = models.TextField('API描述', blank=True)
    doc_url = models.URLField('文档链接', blank=True)
    target_url = models.URLField('目标URL', blank=True, help_text='实际调用的API地址')
    headers = models.JSONField('自定义请求头', default=dict, blank=True)
    parameters = models.JSONField('默认参数', default=dict, blank=True)
    is_active = models.BooleanField('是否启用', default=True)
    is_public = models.BooleanField('是否公开', default=True, help_text='公开API无需认证即可调用')
    rate_limit = models.IntegerField('速率限制(次/分钟)', default=60)
    price = models.DecimalField('单价(元/次)', max_digits=10, decimal_places=4, default=0)
    timeout = models.IntegerField('超时时间(秒)', default=30)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'api_endpoints'
        verbose_name = 'API端点'
        verbose_name_plural = 'API端点'
        ordering = ['category', 'path']
    
    def __str__(self):
        return f"{self.name} ({self.method} {self.path})"


class APIAccessLog(models.Model):
    """API访问记录"""
    api_key = models.ForeignKey(APIKey, on_delete=models.SET_NULL, null=True, related_name='access_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='access_logs')
    endpoint = models.ForeignKey(APIEndpoint, on_delete=models.SET_NULL, null=True, related_name='access_logs')
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
    created_at = models.DateTimeField('访问时间', auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'api_access_logs'
        verbose_name = 'API访问记录'
        verbose_name_plural = 'API访问记录'
        ordering = ['-created_at']
