from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncHour
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from apps.utils.analytics import PageView
from apps.utils.response import APIResponse


class AnalyticsViewSet:
    """流量统计视图（挂载到AdminDashboardViewSet）"""

    @action(detail=False, methods=['get'], url_path='analytics/summary')
    def analytics_summary(self, request):
        """流量概览（今日/昨日/总计）"""
        now = timezone.now()
        today = now.date()
        yesterday = today - timedelta(days=1)
        month_ago = today - timedelta(days=30)

        # 今日数据
        today_pv = PageView.objects.filter(created_at__date=today).count()
        today_uv = PageView.objects.filter(created_at__date=today).values('session_key').distinct().count()
        today_ips = PageView.objects.filter(created_at__date=today).values('ip_address').distinct().count()

        # 昨日数据
        yesterday_pv = PageView.objects.filter(created_at__date=yesterday).count()
        yesterday_uv = PageView.objects.filter(created_at__date=yesterday).values('session_key').distinct().count()

        # 近30天总计
        month_pv = PageView.objects.filter(created_at__date__gte=month_ago).count()
        month_uv = PageView.objects.filter(created_at__date__gte=month_ago).values('session_key').distinct().count()

        # 总PV/UV/IP
        total_pv = PageView.objects.count()
        total_uv = PageView.objects.values('session_key').distinct().count()
        total_ips = PageView.objects.values('ip_address').distinct().count()

        return APIResponse.success({
            'today': {'pv': today_pv, 'uv': today_uv, 'ips': today_ips},
            'yesterday': {'pv': yesterday_pv, 'uv': yesterday_uv},
            'month': {'pv': month_puv, 'uv': month_uv},
            'total': {'pv': total_pv, 'uv': total_uv, 'ips': total_ips},
        }, '获取成功')

    @action(detail=False, methods=['get'], url_path='analytics/trend')
    def analytics_trend(self, request):
        """PV/UV趋势（按天）"""
        days = int(request.query_params.get('days', 7))
        now = timezone.now()
        start_date = now.date() - timedelta(days=days - 1)

        # 按天分组统计
        trend = (
            PageView.objects
            .filter(created_at__date__gte=start_date)
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(
                pv=Count('id'),
                uv=Count('session_key', distinct=True),
                ips=Count('ip_address', distinct=True),
            )
            .order_by('date')
        )

        result = []
        for item in trend:
            result.append({
                'date': item['date'].strftime('%m-%d'),
                'pv': item['pv'],
                'uv': item['uv'],
                'ips': item['ips'],
            })

        # 补全无数据的日期
        existing_dates = {item['date'] for item in result}
        for i in range(days):
            date = start_date + timedelta(days=i)
            date_str = date.strftime('%m-%d')
            if date_str not in existing_dates:
                result.append({'date': date_str, 'pv': 0, 'uv': 0, 'ips': 0})

        result.sort(key=lambda x: x['date'])
        return APIResponse.success(result, '获取成功')

    @action(detail=False, methods=['get'], url_path='analytics/pages')
    def analytics_pages(self, request):
        """热门页面排行"""
        limit = int(request.query_params.get('limit', 10))
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        queryset = PageView.objects.all()
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        pages = (
            queryset
            .values('path')
            .annotate(pv=Count('id'), uv=Count('session_key', distinct=True))
            .order_by('-pv')
            [:limit]
        )

        result = [{'path': item['path'], 'pv': item['pv'], 'uv': item['uv']} for item in pages]
        return APIResponse.success(result, '获取成功')

    @action(detail=False, methods=['get'], url_path='analytics/sources')
    def analytics_sources(self, request):
        """访问来源分析"""
        limit = int(request.query_params.get('limit', 10))
        sources = (
            PageView.objects
            .exclude(referer='')
            .values('referer')
            .annotate(count=Count('id'))
            .order_by('-count')
            [:limit]
        )
        result = [{'referer': item['referer'], 'count': item['count']} for item in sources]
        return APIResponse.success(result, '获取成功')

    @action(detail=False, methods=['get'], url_path='analytics/realtime')
    def analytics_realtime(self, request):
        """实时在线（近5分钟PV/UV）"""
        now = timezone.now()
        five_mins_ago = now - timedelta(minutes=5)

        recent = PageView.objects.filter(created_at__gte=five_mins_ago)
        pv = recent.count()
        uv = recent.values('session_key').distinct().count()
        ips = recent.values('ip_address').distinct().count()

        # 最近访问记录
        recent_logs = recent.order_by('-created_at')[:20]
        logs = []
        for log in recent_logs:
            logs.append({
                'path': log.path,
                'ip': log.ip_address or '未知',
                'username': log.user.username if log.user else '匿名',
                'time': log.created_at.strftime('%H:%M:%S'),
            })

        return APIResponse.success({
            'pv': pv,
            'uv': uv,
            'ips': ips,
            'logs': logs,
        }, '获取成功')
