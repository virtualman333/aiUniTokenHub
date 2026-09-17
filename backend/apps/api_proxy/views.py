import json
import time
import httpx
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from .models import APIAccessLog
from .serializers import ProxyRequestSerializer, APIAccessLogSerializer, AccessLogStatSerializer
from apps.users.models import APIKey, UsageLog
from apps.utils.response import APIResponse
# 「本地某一天」→ 带时区瞬间。**不要在这里用 `TruncDate` / `__date`** ——
# 见 apps/utils/timerange.py 的模块 docstring（MySQL 没装时区表时恒 NULL）。
from apps.utils.timerange import dates_between, local_day_bounds


class ProxyAccessViewSet(viewsets.GenericViewSet):
    """代理访问"""
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get', 'post', 'put', 'delete', 'patch'])
    def forward(self, request):
        """通用代理转发"""
        path = request.data.get('path') or request.query_params.get('path')
        target_url = request.data.get('target_url') or request.query_params.get('target_url')
        
        if not path or not target_url:
            return APIResponse.error('缺少path或target_url参数', 400)
        
        start_time = time.time()
        
        try:
            with httpx.Client(timeout=30) as client:
                response = client.request(
                    method=request.method,
                    url=target_url,
                    headers=dict(request.headers),
                    params=request.query_params,
                    json=request.data if request.data else None,
                )
            
            response_time = int((time.time() - start_time) * 1000)
            
            return APIResponse.success({
                'data': response.json() if 'application/json' in response.headers.get('content-type', '') else response.text,
                'status': response.status_code,
                'response_time': response_time,
            }, '请求成功')
            
        except Exception as e:
            return APIResponse.error(str(e), 500)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdminUser])
    def access_logs(self, request):
        """接口使用记录列表"""
        queryset = APIAccessLog.objects.select_related('user', 'api_key').all()
        
        # 按路径筛选
        path = request.query_params.get('path')
        if path:
            queryset = queryset.filter(path__icontains=path)
        
        # 按请求方法筛选
        method = request.query_params.get('method')
        if method:
            queryset = queryset.filter(method=method.upper())
        
        # 按用户名筛选
        username = request.query_params.get('username')
        if username:
            queryset = queryset.filter(user__username__icontains=username)
        
        # 按API Key筛选
        api_key_id = request.query_params.get('api_key_id')
        if api_key_id:
            queryset = queryset.filter(api_key_id=int(api_key_id))
        
        # 按状态码范围筛选
        status_gte = request.query_params.get('status_gte')
        status_lt = request.query_params.get('status_lt')
        if status_gte and status_lt:
            queryset = queryset.filter(response_status__gte=int(status_gte), response_status__lt=int(status_lt))
        
        # 按成功/失败筛选
        success = request.query_params.get('success')
        if success == 'true':
            queryset = queryset.filter(response_status__gte=200, response_status__lt=400)
        elif success == 'false':
            queryset = queryset.filter(Q(response_status__gte=400) | Q(response_status=0))
        
        # 按响应时间筛选
        response_time_gte = request.query_params.get('response_time_gte')
        response_time_lt = request.query_params.get('response_time_lt')
        if response_time_gte:
            queryset = queryset.filter(response_time__gte=int(response_time_gte))
        if response_time_lt:
            queryset = queryset.filter(response_time__lt=int(response_time_lt))
        
        # 按IP地址筛选
        ip_address = request.query_params.get('ip_address')
        if ip_address:
            queryset = queryset.filter(ip_address__icontains=ip_address)
        
        # 按时间范围筛选。
        #
        # 这两个参数**刻意**不走 `apps/utils/timerange.parse_day_bound`，也不做
        # 「整天」展开：调用方 `frontend/src/views/admin/AccessLogs.vue` 传的是
        # `dayjs(...).startOf('day')` / `.endOf('day')` 的 `toISOString()`，
        # 也就是两端都是精确到毫秒的**瞬间**，且上界本身是**闭**的
        # （`...T15:59:59.999Z`）。当成整天展开会把窗口放宽小半天，改成 `<` 又会
        # 把最后一毫秒切掉。账单那个接口（`apps/users/views.py::admin-bills`）的
        # 前端传的是 `YYYY-MM-DD`，形态不同，那边才需要半开区间。
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        queryset = queryset.order_by('-created_at')
        
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        start = (page - 1) * page_size
        end = start + page_size
        
        total = queryset.count()
        logs = queryset[start:end]
        
        serializer = APIAccessLogSerializer(logs, many=True)
        return APIResponse.paginated(serializer.data, total, page, page_size, '获取成功')
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdminUser])
    def access_stats(self, request):
        """接口使用统计"""
        days = int(request.query_params.get('days', 7))
        days = min(days, 30)  # 最多30天
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # 按日期分组统计。
        #
        # 原来这里是 `.annotate(date=TruncDate('created_at'))`：Django 在 MySQL 上
        # 会把它编译成 `DATE(CONVERT_TZ(created_at, 'UTC', 'Asia/Shanghai'))`，
        # 而 MySQL 默认没装时区表（`mysql.time_zone_name` 不存在）→ `CONVERT_TZ`
        # 返回 **NULL**。于是分组键全是 NULL：所有行塌进同一个 `{'date': None}` 的组，
        # 而 `AccessLogStatSerializer.date` 是 `DateField()`（不允许 None）——
        # 这个接口当时是直接 500 的，不是「少几行数据」。
        #
        # 改成按本地日逐天聚合：SQL 里只剩 `created_at >= ? AND created_at < ?`，
        # 不依赖数据库时区表。首尾两天各只覆盖半天，所以与窗口取交集 ——
        # 这样与「按本地日分组」的结果逐行等价（不重不漏）。
        stats = []
        local_tz = timezone.get_current_timezone()
        for day in dates_between(start_date.astimezone(local_tz).date(),
                                 end_date.astimezone(local_tz).date()):
            day_start, day_end = local_day_bounds(day)
            bucket_start = max(day_start, start_date)
            bucket_end = min(day_end, end_date)
            if bucket_start >= bucket_end:
                continue
            bucket = APIAccessLog.objects.filter(
                created_at__gte=bucket_start,
                created_at__lt=bucket_end,
            ).aggregate(
                total_count=Count('id'),
                success_count=Count('id', filter=Q(response_status__gte=200, response_status__lt=400)),
                error_count=Count('id', filter=Q(response_status__gte=400)),
                avg_response_time=Avg('response_time'),
            )
            if not bucket['total_count']:
                continue
            stats.append({
                'date': day,
                'total_count': bucket['total_count'],
                'success_count': bucket['success_count'],
                'error_count': bucket['error_count'],
                # `Avg` 在全为 NULL 时给 None，而序列化器是 FloatField —— 兜 0
                'avg_response_time': bucket['avg_response_time'] or 0,
            })
        
        serializer = AccessLogStatSerializer(stats, many=True)
        
        # 总览统计
        total_logs = APIAccessLog.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        overview = {
            'total_count': total_logs.count(),
            'success_count': total_logs.filter(response_status__gte=200, response_status__lt=400).count(),
            'error_count': total_logs.filter(response_status__gte=400).count(),
            'avg_response_time': total_logs.aggregate(avg=Avg('response_time'))['avg'] or 0,
            'max_response_time': total_logs.order_by('-response_time').first().response_time if total_logs.exists() else 0,
        }
        
        # 按用户统计
        user_stats = APIAccessLog.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).select_related('user').values(
            'user__username'
        ).annotate(
            count=Count('id'),
            avg_time=Avg('response_time')
        ).order_by('-count')[:10]
        
        # 按状态码分布
        status_distribution = APIAccessLog.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).values('response_status').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        return APIResponse.success({
            'overview': overview,
            'daily_stats': serializer.data,
            'user_stats': list(user_stats),
            'status_distribution': list(status_distribution),
        })
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsAdminUser])
    def access_log_detail(self, request, pk=None):
        """接口使用记录详情"""
        try:
            log = APIAccessLog.objects.select_related('user', 'api_key').get(pk=pk)
        except APIAccessLog.DoesNotExist:
            return APIResponse.error('日志不存在', 404)
        
        serializer = APIAccessLogSerializer(log)
        return APIResponse.success(serializer.data)
