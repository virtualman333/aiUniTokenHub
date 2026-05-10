"""
流量统计视图 - 全部基于Redis查询
"""
import json
from datetime import date, timedelta
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from apps.utils.analytics import (
    get_analytics_from_redis,
    get_realtime_from_redis,
    get_summary_from_redis,
    _get_redis,
)
from apps.utils.response import APIResponse


class AnalyticsViewSet:
    """流量统计视图（挂载到AdminDashboardViewSet）- 基于Redis"""

    @action(detail=False, methods=['get'], url_path='analytics/summary')
    def analytics_summary(self, request):
        """流量概览（今日/昨日/周/月/总计）- 从Redis读取"""
        data = get_summary_from_redis()
        return APIResponse.success(data, '获取成功')

    @action(detail=False, methods=['get'], url_path='analytics/trend')
    def analytics_trend(self, request):
        """PV/UV趋势（按天）- 从Redis读取"""
        days = int(request.query_params.get('days', 30))
        records = get_analytics_from_redis(days=days)

        # 转换为前端格式
        result = []
        for item in records:
            d = item['date']
            result.append({
                'date': d[5:],  # "2026-05-10" -> "05-10"
                'pv': item['pv'],
                'uv': item['uv'],
                'ips': item['ips'],
            })

        # 按日期正序排列
        result.reverse()
        return APIResponse.success(result, '获取成功')

    @action(detail=False, methods=['get'], url_path='analytics/pages')
    def analytics_pages(self, request):
        """热门页面排行 - 从Redis读取"""
        days = min(int(request.query_params.get('days', 7)), 30)
        limit = int(request.query_params.get('limit', 10))
        r = _get_redis()

        today = date.today()
        page_stats = {}  # {path: {'pv': N, 'uv_set': set()}}

        for i in range(days):
            d = (today - timedelta(days=i)).strftime('%Y-%m-%d')
            # 扫描所有路径键
            pattern = f'analytics:path:{d}:*'
            cursor = 0
            while True:
                cursor, keys = r.scan(cursor=cursor, match=pattern, count=100)
                if not keys:
                    break
                for key in keys:
                    path = key.split(f'analytics:path:{d}:')[-1].replace(':', '/')
                    pv = int(r.get(key) or 0)
                    if path not in page_stats:
                        page_stats[path] = {'pv': 0, 'uv_set': set()}
                    page_stats[path]['pv'] += pv
                if cursor == 0:
                    break

        # 排序取前N
        sorted_pages = sorted(page_stats.items(), key=lambda x: x[1]['pv'], reverse=True)[:limit]
        result = [{'path': p, 'pv': s['pv']} for p, s in sorted_pages]
        return APIResponse.success(result, '获取成功')

    @action(detail=False, methods=['get'], url_path='analytics/sources')
    def analytics_sources(self, request):
        """访问来源分析 - 从Redis队列中统计"""
        limit = int(request.query_params.get('limit', 10))
        r = _get_redis()

        # 从队列中采样最近1万条记录统计来源
        recent = r.lrange('analytics:queue', 0, 9999)
        source_count = {}
        for item in recent:
            try:
                log = json.loads(item)
                ref = log.get('referer', '')
                if ref:
                    # 简化域名提取
                    domain = ref.split('/')[2] if '/' in ref else ref
                    source_count[domain] = source_count.get(domain, 0) + 1
            except Exception:
                pass

        sorted_sources = sorted(source_count.items(), key=lambda x: x[1], reverse=True)[:limit]
        result = [{'referer': domain, 'count': cnt} for domain, cnt in sorted_sources]
        return APIResponse.success(result, '获取成功')

    @action(detail=False, methods=['get'], url_path='analytics/realtime')
    def analytics_realtime(self, request):
        """实时在线（近5分钟PV/UV/IP）- 从Redis读取"""
        data = get_realtime_from_redis()
        return APIResponse.success(data, '获取成功')

    @action(detail=False, methods=['get'], url_path='analytics/records')
    def analytics_records(self, request):
        """
        每日访问记录汇总列表 - 从Redis读取
        支持按日期范围筛选，返回每日聚合的PV/UV/IP
        """
        start_date_str = request.query_params.get('start_date', '')
        end_date_str = request.query_params.get('end_date', '')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))

        today = date.today()

        # 默认查近30天
        default_days = 30
        if start_date_str:
            try:
                start_d = date.fromisoformat(start_date_str)
                days_from_start = (today - start_d).days + 1
                default_days = max(default_days, days_from_start)
            except ValueError:
                pass

        all_records = get_analytics_from_redis(days=default_days)

        # 按日期筛选
        if start_date_str or end_date_str:
            filtered = []
            for r in all_records:
                include = True
                if start_date_str and r['date'] < start_date_str:
                    include = False
                if end_date_str and r['date'] > end_date_str:
                    include = False
                if include:
                    filtered.append(r)
            all_records = filtered

        total = len(all_records)
        total_pv = sum(r['pv'] for r in all_records)
        total_uv = sum(r['uv'] for r in all_records)
        total_ips = sum(r['ips'] for r in all_records)

        # 分页（按日期倒序）
        all_records.reverse()  # 最新在前
        start = (page - 1) * page_size
        end = start + page_size
        paged = all_records[start:end]

        return APIResponse.success({
            'total_pv': total_pv,
            'total_uv': total_uv,
            'total_ips': total_ips,
            'page': page,
            'page_size': page_size,
            'total': total,
            'data': paged,
        }, '获取成功')
