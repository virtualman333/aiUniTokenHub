from django.db import models
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class PageView(models.Model):
    """页面访问记录（PV/UV统计）"""

    # 访问用户（匿名用户为None）
    user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='page_views',
        verbose_name='用户'
    )
    # 会话标识（用于UV统计，未登录用户用session_key或随机标识）
    session_key = models.CharField('会话标识', max_length=128, blank=True, default='')
    # 访问IP
    ip_address = models.GenericIPAddressField('IP地址', null=True, blank=True)
    # 访问路径
    path = models.CharField('访问路径', max_length=500, db_index=True)
    # 访问来源页
    referer = models.URLField('来源页', blank=True, default='')
    # 用户代理
    user_agent = models.TextField('UA信息', blank=True, default='')
    # 访问时间
    created_at = models.DateTimeField('访问时间', auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'page_views'
        verbose_name = '页面访问记录'
        verbose_name_plural = '页面访问记录'
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.ip_address or "未知IP"} {self.path}'


def get_client_ip(request):
    """获取客户端真实IP"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class AnalyticsMiddleware:
    """流量统计中间件"""

    # 排除的路径（API、静态文件、WebSocket等）
    EXCLUDE_PATHS = [
        '/admin/',
        '/static/',
        '/media/',
        '/ws/',
        '/favicon.ico',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 排除指定路径
        path = request.path
        if any(path.startswith(p) for p in self.EXCLUDE_PATHS):
            return self.get_response(request)

        # 只统计GET请求（页面访问）
        if request.method != 'GET':
            return self.get_response(request)

        # 获取请求信息
        ip_address = get_client_ip(request)
        user = request.user if request.user.is_authenticated else None
        session_key = request.session.session_key or ''

        # 获取UA和来源
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        referer = request.META.get('HTTP_REFERER', '')

        # 异步记录（简单实现：直接保存，高并发可改为Celery任务）
        try:
            PageView.objects.create(
                user=user,
                session_key=session_key,
                ip_address=ip_address,
                path=path[:500],  # 截断过长路径
                referer=referer[:200] if referer else '',
                user_agent=user_agent[:500] if user_agent else '',
            )
        except Exception as e:
            logger.error(f'记录PV失败: {e}')

        return self.get_response(request)
