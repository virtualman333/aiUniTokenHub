from django.db import models
from apps.users.models import User, APIKey


class APIAccessLog(models.Model):
    """API访问记录"""
    api_key = models.ForeignKey(APIKey, on_delete=models.SET_NULL, null=True, related_name='access_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='access_logs')
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
