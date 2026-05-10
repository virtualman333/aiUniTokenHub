"""
流量统计中间件 - Redis版本
使用Redis进行实时聚合统计，避免频繁数据库IO

Redis 数据结构设计：
  - PV计数器:     analytics:pv:{date}          (String/INCR)
  - UV去重:       analytics:uv:{date}          (HyperLogLog/PFADD)
  - IP去重:       analytics:ip:{date}          (Set/SADD)
  - 路径PV:       analytics:path:{date}:{path} (String/INCR, TTL=7天)
  - 记录缓冲队列:  analytics:queue              (List/LPUSH, 最大10万条)
  - 实时在线:     analytics:realtime            (Key带TTL 5分钟)
"""
import json
import redis
from datetime import date
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

# Redis连接池（全局复用）
_redis_pool = None


def _get_redis():
    """获取Redis连接（使用连接池）"""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL, max_connections=20)
    return redis.Redis(connection_pool=_redis_pool)


def get_client_ip(request):
    """获取客户端真实IP"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class AnalyticsMiddleware:
    """流量统计中间件 - Redis版"""

    # 排除的路径
    EXCLUDE_PATHS = [
        '/admin/',
        '/static/',
        '/media/',
        '/ws/',
        '/favicon.ico',
        '/api/admin/analytics/',  # 排除自身统计接口的请求
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        # 排除指定路径
        if any(path.startswith(p) for p in self.EXCLUDE_PATHS):
            return self.get_response(request)

        # 只统计GET请求
        if request.method != 'GET':
            return self.get_response(request)

        try:
            self._record_to_redis(request)
        except Exception as e:
            logger.warning(f'Redis记录PV失败(不影响用户): {e}')

        return self.get_response(request)

    def _record_to_redis(self, request):
        """将访问记录写入Redis（Pipeline批量操作）"""
        r = _get_redis()
        pipe = r.pipeline(transaction=False)  # 非事务pipeline，更快

        today = date.today().strftime('%Y-%m-%d')
        path = request.path[:500]
        ip_address = get_client_ip(request)
        session_key = request.session.session_key or ''
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        referer = request.META.get('HTTP_REFERER', '')[:200]
        user_id = request.user.id if request.user.is_authenticated else None
        username = request.user.username if request.user.is_authenticated else ''

        now_ts = timezone.now().strftime('%Y-%m-%d %H:%M:%S')

        # === 1. 今日PV +1 ===
        pipe.incrby(f'analytics:pv:{today}', 1)
        # 设置7天过期（自动清理旧数据）
        pipe.expire(f'analytics:pv:{today}', 86400 * 7)

        # === 2. UV去重 (HyperLogLog，内存占用极低) ===
        pipe.pfadd(f'analytics:uv:{today}', session_key or f'anon_{ip_address}')
        pipe.expire(f'analytics:uv:{today}', 86400 * 7)

        # === 3. 独立IP去重 (Set) ===
        if ip_address:
            pipe.sadd(f'analytics:ip:{today}', ip_address)
            pipe.expire(f'analytics:ip:{today}', 86400 * 7)

        # === 4. 路径级别PV ===
        safe_path = path.replace('/', ':') or 'root'
        pipe.incrby(f'analytics:path:{today}:{safe_path}', 1)
        pipe.expire(f'analytics:path:{today}:{safe_path}', 86400 * 7)

        # === 5. 实时在线（5分钟窗口内的PV/UV/IP） ===
        realtime_key = f'analytics:realtime'
        pipe.incrby(f'{realtime_key}:pv', 1)
        pipe.expire(f'{realtime_key}:pv', 300)
        pipe.pfadd(f'{realtime_key}:uv', session_key or f'anon_{ip_address}')
        pipe.expire(f'{realtime_key}:uv', 300)
        if ip_address:
            pipe.sadd(f'{realtime_key}:ips', ip_address)
            pipe.expire(f'{realtime_key}:ips', 300)

        # === 6. 写入缓冲队列（用于需要详细记录的场景，限制长度防内存溢出）===
        record = json.dumps({
            'path': path,
            'ip_address': ip_address or '',
            'session_key': session_key,
            'user_id': user_id,
            'username': username,
            'referer': referer,
            'user_agent': user_agent,
            'created_at': now_ts,
        }, ensure_ascii=False)
        pipe.lpush('analytics:queue', record)
        # 队列最多保留10万条
        pipe.ltrim('analytics:queue', 0, 100000)

        # 一次性发送所有命令
        pipe.execute()


def get_analytics_from_redis(days=None):
    """
    从Redis获取多天统计数据
    返回: [{'date': '2026-05-10', 'pv': 123, 'uv': 45, 'ips': 12}, ...]
    """
    r = _get_redis()
    if days is None:
        days = 30

    results = []
    today = date.today()

    for i in range(days):
        d = (today - __import__('datetime').timedelta(days=i)).strftime('%Y-%m-%d')
        pipe = r.pipeline(transaction=False)
        pv_key = f'analytics:pv:{d}'
        uv_key = f'analytics:uv:{d}'
        ip_key = f'analytics:ip:{d}'

        pipe.get(pv_key)
        pipe.pfcount(uv_key)
        pipe.scard(ip_key)

        result = pipe.execute()
        pv = int(result[0] or 0)
        uv = int(result[1] or 0)
        ips = int(result[2] or 0)

        results.append({
            'date': d,
            'pv': pv,
            'uv': uv,
            'ips': ips,
        })

    return results


def get_realtime_from_redis():
    """获取实时在线数据（近5分钟）"""
    r = _get_redis()
    pipe = r.pipeline(transaction=False)
    pipe.get('analytics:realtime:pv')
    pipe.pfcount('analytics:realtime:uv')
    pipe.scard('analytics:realtime:ips')

    # 最近20条访问记录
    pipe.lrange('analytics:queue', 0, 19)

    result = pipe.execute()
    pv = int(result[0] or 0)
    uv = int(result[1] or 0)
    ips = int(result[2] or 0)

    logs = []
    for item in result[3]:
        try:
            log = json.loads(item)
            logs.append({
                'path': log.get('path', ''),
                'ip': log.get('ip_address', '未知'),
                'username': log.get('username', '匿名'),
                'time': log.get('created_at', '')[-8:],  # 只取HH:mm:ss
            })
        except Exception:
            pass

    return {
        'pv': pv,
        'uv': uv,
        'ips': ips,
        'logs': logs,
    }


def get_summary_from_redis():
    """从Redis获取概览统计数据（今日/昨日/本周/本月/总计）"""
    r = _get_redis()
    today = date.today()
    yesterday = (today - __import__('datetime').timedelta(days=1)).strftime('%Y-%m-%d')
    today_str = today.strftime('%Y-%m-%d')
    week_ago = (today - __import__('datetime').timedelta(days=today.weekday())).strftime('%Y-%m-%d')
    month_start = today.replace(day=1).strftime('%Y-%m-%d')

    # 各时间段的所有日期
    all_dates = []
    for i in range(90):  # 最多查90天
        d = (today - __import__('datetime').timedelta(days=i)).strftime('%Y-%m-%d')
        all_dates.append(d)

    week_dates = [d for d in all_dates if d >= week_ago]
    month_dates = [d for d in all_dates if d >= month_start]

    def _sum_range(date_list, key_fn):
        """对一组日期求和"""
        pipe = r.pipeline(transaction=False)
        for d in date_list:
            if key_fn == 'pv':
                pipe.get(f'analytics:pv:{d}')
            elif key_fn == 'uv':
                pipe.pfcount(f'analytics:uv:{d}')
            elif key_fn == 'ip':
                pipe.scard(f'analytics:ip:{d}')
        values = pipe.execute()
        total = 0
        for v in values:
            if v is not None:
                total += int(v)
        return total

    # 并行查询所有指标
    pipe = r.pipeline(transaction=False)
    pipe.get(f'analytics:pv:{today_str}')           # 今日PV
    pipe.pfcount(f'analytics:uv:{today_str}')        # 今日UV
    pipe.scard(f'analytics:ip:{today_str}')          # 今日IP
    pipe.get(f'analytics:pv:{yesterday}')            # 昨日PV
    pipe.pfcount(f'analytics:uv:{yesterday}')        # 昨日UV
    base_result = pipe.execute()

    today_pv = int(base_result[0] or 0)
    today_uv = int(base_result[1] or 0)
    today_ips = int(base_result[2] or 0)
    yesterday_pv = int(base_result[3] or 0)
    yesterday_uv = int(base_result[4] or 0)

    # 范围汇总（周、月、总）
    week_pv = _sum_range(week_dates, 'pv')
    month_pv = _sum_range(month_dates, 'pv')
    total_pv = _sum_range(all_dates, 'pv')
    week_uv = _sum_range(week_dates, 'uv')
    month_uv = _sum_range(month_dates, 'uv')
    total_uv = _sum_range(all_dates, 'uv')

    return {
        'today': {'pv': today_pv, 'uv': today_uv, 'ips': today_ips},
        'yesterday': {'pv': yesterday_pv, 'uv': yesterday_uv},
        'week': {'pv': week_pv, 'uv': week_uv},
        'month': {'pv': month_pv, 'uv': month_uv},
        'total': {'pv': total_pv, 'uv': total_uv},
    }
