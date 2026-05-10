"""
Redis管理相关的API视图
"""
import datetime
import json
import redis
from django.conf import settings
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import viewsets
from rest_framework import status
from apps.utils.response import APIResponse


class RedisManagementViewSet(viewsets.ViewSet):
    """Redis管理API"""
    permission_classes = [IsAdminUser]
    
    def _get_redis_connection(self):
        """获取Redis连接"""
        redis_url = settings.REDIS_URL
        return redis.from_url(redis_url)
    
    @action(detail=False, methods=['get'])
    def info(self, request):
        """获取Redis信息"""
        try:
            r = self._get_redis_connection()
            
            # 获取Redis信息
            info = r.info()
            
            # 提取关键信息
            result = {
                'version': info.get('redis_version', 'Unknown'),
                'uptime_in_seconds': info.get('uptime_in_seconds', 0),
                'uptime_in_days': info.get('uptime_in_days', 0),
                'connected_clients': info.get('connected_clients', 0),
                'used_memory': info.get('used_memory', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'used_memory_peak': info.get('used_memory_peak', 0),
                'used_memory_peak_human': info.get('used_memory_peak_human', '0B'),
                'total_connections_received': info.get('total_connections_received', 0),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'instantaneous_ops_per_sec': info.get('instantaneous_ops_per_sec', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'expired_keys': info.get('expired_keys', 0),
                'evicted_keys': info.get('evicted_keys', 0),
                'keys': self._get_key_count(r),
            }
            
            r.close()
            return APIResponse.success(result)
        except Exception as e:
            return APIResponse.error(f'获取Redis信息失败: {str(e)}', 500)
    
    def _get_key_count(self, r):
        """获取所有数据库的key数量"""
        try:
            info = r.info('keyspace')
            total = 0
            for db_info in info.values():
                total += db_info.get('keys', 0)
            return total
        except:
            return 0
    
    @action(detail=False, methods=['get'])
    def keys(self, request):
        """获取Redis键列表"""
        try:
            r = self._get_redis_connection()
            
            # 获取参数
            pattern = request.query_params.get('pattern', '*')
            cursor = int(request.query_params.get('cursor', 0))
            count = int(request.query_params.get('count', 100))
            
            # 使用SCAN命令获取键列表
            keys = []
            for key in r.scan_iter(match=pattern, count=count):
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                key_type = r.type(key).decode('utf-8') if isinstance(r.type(key), bytes) else r.type(key)
                
                # 获取TTL
                ttl = r.ttl(key)
                
                keys.append({
                    'key': key_str,
                    'type': key_type,
                    'ttl': ttl,
                    'size': self._get_key_size(r, key, key_type),
                })
            
            r.close()
            
            return APIResponse.success({
                'keys': keys[:count],
                'total': len(keys),
                'cursor': cursor + 1 if keys else 0,
            })
        except Exception as e:
            return APIResponse.error(f'获取Redis键列表失败: {str(e)}', 500)
    
    def _get_key_size(self, r, key, key_type):
        """获取键的大小"""
        try:
            if key_type == 'string':
                return r.strlen(key)
            elif key_type == 'list':
                return r.llen(key)
            elif key_type == 'set':
                return r.scard(key)
            elif key_type == 'zset':
                return r.zcard(key)
            elif key_type == 'hash':
                return r.hlen(key)
            else:
                return 0
        except:
            return 0
    
    @action(detail=False, methods=['get'])
    def key_detail(self, request):
        """获取键详情"""
        try:
            r = self._get_redis_connection()
            
            key = request.query_params.get('key')
            if not key:
                return APIResponse.error('缺少key参数', 400)
            
            # 检查键是否存在
            if not r.exists(key):
                return APIResponse.error('键不存在', 404)
            
            # 获取键类型
            key_type = r.type(key).decode('utf-8') if isinstance(r.type(key), bytes) else r.type(key)
            
            # 获取TTL
            ttl = r.ttl(key)
            
            # 根据类型获取值
            value = None
            if key_type == 'string':
                value = r.get(key)
                if isinstance(value, bytes):
                    try:
                        value = value.decode('utf-8')
                        # 尝试解析JSON
                        value = json.loads(value)
                    except:
                        pass
            elif key_type == 'list':
                value = r.lrange(key, 0, -1)
                value = [v.decode('utf-8') if isinstance(v, bytes) else v for v in value]
            elif key_type == 'set':
                value = list(r.smembers(key))
                value = [v.decode('utf-8') if isinstance(v, bytes) else v for v in value]
            elif key_type == 'zset':
                value = r.zrange(key, 0, -1, withscores=True)
                value = [(k.decode('utf-8') if isinstance(k, bytes) else k, s) for k, s in value]
            elif key_type == 'hash':
                value = r.hgetall(key)
                value = {k.decode('utf-8') if isinstance(k, bytes) else k: 
                         v.decode('utf-8') if isinstance(v, bytes) else v 
                         for k, v in value.items()}
            
            r.close()
            
            return APIResponse.success({
                'key': key,
                'type': key_type,
                'ttl': ttl,
                'value': value,
            })
        except Exception as e:
            return APIResponse.error(f'获取键详情失败: {str(e)}', 500)
    
    @action(detail=False, methods=['post'])
    def delete_key(self, request):
        """删除键"""
        try:
            r = self._get_redis_connection()
            
            key = request.data.get('key')
            if not key:
                return APIResponse.error('缺少key参数', 400)
            
            # 删除键
            result = r.delete(key)
            
            r.close()
            
            if result:
                return APIResponse.success(None, '删除成功')
            else:
                return APIResponse.error('键不存在', 404)
        except Exception as e:
            return APIResponse.error(f'删除键失败: {str(e)}', 500)
    
    @action(detail=False, methods=['post'])
    def flush_db(self, request):
        """清空当前数据库"""
        try:
            r = self._get_redis_connection()
            
            # 清空数据库
            r.flushdb()
            
            r.close()
            
            return APIResponse.success(None, '清空成功')
        except Exception as e:
            return APIResponse.error(f'清空数据库失败: {str(e)}', 500)

    @action(detail=False, methods=['post'])
    def set_key(self, request):
        """修改/新增键值"""
        try:
            r = self._get_redis_connection()
            
            key = request.data.get('key')
            value = request.data.get('value')
            key_type = request.data.get('type', 'string')
            ttl = request.data.get('ttl', -1)  # -1表示不设置过期时间
            
            if not key or value is None:
                return APIResponse.error('缺少key或value参数', 400)
            
            # 根据类型设置值
            if key_type == 'string':
                r.set(key, str(value))
            elif key_type == 'hash':
                # value格式：{"field1": "value1", "field2": "value2"}
                r.delete(key)  # 先删除原有数据
                r.hset(key, mapping=value)
            elif key_type == 'list':
                # value格式：["item1", "item2"]
                r.delete(key)
                r.rpush(key, *value)
            elif key_type == 'set':
                # value格式：["member1", "member2"]
                r.delete(key)
                r.sadd(key, *value)
            elif key_type == 'zset':
                # value格式：[("member1", 1), ("member2", 2)]
                r.delete(key)
                r.zadd(key, dict(value))
            else:
                return APIResponse.error(f'不支持的键类型: {key_type}', 400)
            
            # 设置过期时间
            if int(ttl) > 0:
                r.expire(key, int(ttl))
            
            r.close()
            return APIResponse.success(None, '设置成功')
        except Exception as e:
            return APIResponse.error(f'设置键值失败: {str(e)}', 500)

    @action(detail=False, methods=['post'])
    def set_ttl(self, request):
        """设置键的过期时间"""
        try:
            r = self._get_redis_connection()
            
            key = request.data.get('key')
            ttl = request.data.get('ttl')
            
            if not key or ttl is None:
                return APIResponse.error('缺少key或ttl参数', 400)
            
            if not r.exists(key):
                return APIResponse.error('键不存在', 404)
            
            ttl = int(ttl)
            if ttl == -1:
                # 移除过期时间
                r.persist(key)
            else:
                r.expire(key, ttl)
            
            r.close()
            return APIResponse.success(None, '设置TTL成功')
        except Exception as e:
            return APIResponse.error(f'设置TTL失败: {str(e)}', 500)

    @action(detail=False, methods=['post'])
    def rename_key(self, request):
        """重命名键"""
        try:
            r = self._get_redis_connection()
            
            old_key = request.data.get('old_key')
            new_key = request.data.get('new_key')
            
            if not old_key or not new_key:
                return APIResponse.error('缺少old_key或new_key参数', 400)
            
            if not r.exists(old_key):
                return APIResponse.error('原键不存在', 404)
            
            if r.exists(new_key):
                return APIResponse.error('新键名已存在', 400)
            
            r.rename(old_key, new_key)
            
            r.close()
            return APIResponse.success(None, '重命名成功')
        except Exception as e:
            return APIResponse.error(f'重命名键失败: {str(e)}', 500)

    @action(detail=False, methods=['post'])
    def batch_delete_keys(self, request):
        """批量删除键"""
        try:
            r = self._get_redis_connection()
            
            keys = request.data.get('keys', [])
            pattern = request.data.get('pattern', '')
            
            if not keys and not pattern:
                return APIResponse.error('缺少keys参数或pattern参数', 400)
            
            deleted_count = 0
            if keys:
                # 批量删除指定键
                deleted_count = r.delete(*keys)
            elif pattern:
                # 按模式删除键
                cursor = 0
                while True:
                    cursor, found_keys = r.scan(cursor=cursor, match=pattern, count=100)
                    if found_keys:
                        r.delete(*found_keys)
                        deleted_count += len(found_keys)
                    if cursor == 0:
                        break
            
            r.close()
            return APIResponse.success({'deleted_count': deleted_count}, '批量删除成功')
        except Exception as e:
            return APIResponse.error(f'批量删除失败: {str(e)}', 500)
