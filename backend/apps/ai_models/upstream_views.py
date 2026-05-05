from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils import timezone
import random

from .models import AIModel, ModelProvider
from .upstream_models import UpstreamAccount, ModelUpstreamAccount
from .upstream_serializers import (
    UpstreamAccountSerializer, UpstreamAccountListSerializer,
    ModelUpstreamAccountSerializer, ModelUpstreamAccountCreateSerializer
)
from apps.utils.response import APIResponse


class UpstreamAccountViewSet(viewsets.ModelViewSet):
    """上游账号管理"""
    queryset = UpstreamAccount.objects.all()
    permission_classes = [IsAdminUser]
    
    def get_serializer_class(self):
        if self.action in ['list']:
            return UpstreamAccountListSerializer
        return UpstreamAccountSerializer
    
    def create(self, request, *args, **kwargs):
        """创建上游账号后自动获取并添加模型"""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.error(str(serializer.errors), 400)
        
        instance = serializer.save()
        
        # 自动获取并添加模型
        added_count = self._fetch_and_add_models(instance)
        
        return APIResponse.created(
            {**serializer.data, 'models_added': added_count},
            f'创建成功，已自动添加 {added_count} 个模型'
        )
    
    def _fetch_and_add_models(self, account):
        """从上游获取模型列表并添加到数据库"""
        try:
            import httpx
            
            headers = {}
            if account.api_key:
                headers['Authorization'] = f'Bearer {account.api_key}'
            
            # 调用上游模型列表接口
            base_url = account.base_url.rstrip('/')
            response = httpx.get(
                f"{base_url}/models",
                headers=headers,
                timeout=15
            )
            
            if response.status_code != 200:
                return 0
            
            data = response.json()
            models_data = data.get('data', []) if isinstance(data, dict) else []
            
            if not models_data:
                return 0
            
            added_count = 0
            for model_info in models_data:
                model_id = model_info.get('id', '')
                if not model_id:
                    continue
                
                # 检查是否已存在
                if AIModel.objects.filter(code=model_id).exists():
                    continue
                
                # 自动获取供应商
                provider = self._get_or_create_provider(base_url, account)
                
                # 创建模型
                AIModel.objects.create(
                    code=model_id,
                    name=model_id,
                    provider=provider,
                    status='inactive',  # 新添加的模型默认不启用
                    description=model_info.get('ready', True) and '可用' or '未知',
                )
                added_count += 1
            
            # 更新账号状态
            account.is_available = True
            account.last_error = ''
            account.save(update_fields=['is_available', 'last_error'])
            
            return added_count
            
        except Exception as e:
            # 记录错误但不影响账号创建
            import traceback
            traceback.print_exc()
            return 0
    
    def _get_or_create_provider(self, base_url, account):
        """根据base_url获取或创建供应商"""
        # 从base_url提取供应商标识
        provider_code = ''
        if 'openai' in base_url.lower():
            provider_code = 'openai'
        elif 'anthropic' in base_url.lower():
            provider_code = 'anthropic'
        elif 'deepseek' in base_url.lower():
            provider_code = 'deepseek'
        elif 'zhipu' in base_url.lower() or '智谱' in base_url:
            provider_code = 'zhipu'
        elif 'baidu' in base_url.lower() or '百度' in base_url:
            provider_code = 'baidu'
        elif 'ali' in base_url.lower() or '阿里' in base_url:
            provider_code = 'aliyun'
        elif 'moonshot' in base_url.lower() or '月之暗面' in base_url:
            provider_code = 'moonshot'
        elif 'minimax' in base_url.lower():
            provider_code = 'minimax'
        elif 'gemini' in base_url.lower():
            provider_code = 'gemini'
        else:
            provider_code = 'custom'
        
        provider, _ = ModelProvider.objects.get_or_create(
            code=provider_code,
            defaults={
                'name': provider_code.upper(),
                'is_active': True,
            }
        )
        
        return provider
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """获取启用的账号（按供应商筛选）"""
        provider_id = request.query_params.get('provider')
        queryset = self.queryset.filter(is_active=True)
        if provider_id:
            queryset = queryset.filter(provider_id=provider_id)
        serializer = UpstreamAccountListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """测试账号连接"""
        account = self.get_object()
        try:
            import httpx
            headers = {'Authorization': f'Bearer {account.api_key}'}
            # 简单测试：获取模型列表
            response = httpx.get(
                f"{account.base_url.rstrip('/')}/models",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                account.is_available = True
                account.last_error = ''
                account.save()
                return APIResponse.success({'status': 'ok'}, '连接成功')
            else:
                account.is_available = False
                account.last_error = f'HTTP {response.status_code}'
                account.save()
                return APIResponse.error(f'连接失败: HTTP {response.status_code}', 400)
        except Exception as e:
            account.is_available = False
            account.last_error = str(e)[:500]
            account.save()
            return APIResponse.error(f'连接失败: {str(e)}', 400)
    
    @action(detail=True, methods=['post'])
    def sync_models(self, request, pk=None):
        """从上游账号同步模型列表"""
        account = self.get_object()
        added_count = self._fetch_and_add_models(account)
        return APIResponse.success({'added': added_count}, f'成功同步 {added_count} 个模型')


class ModelUpstreamAccountViewSet(viewsets.GenericViewSet):
    """模型账号关联管理"""
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        return ModelUpstreamAccount.objects.select_related('model', 'account')
    
    @action(detail=False, methods=['get'], url_path='model/(?P<model_id>[^/.]+)')
    def list_by_model(self, request, model_id=None):
        """获取模型的关联账号"""
        bindings = self.get_queryset().filter(model_id=model_id)
        serializer = ModelUpstreamAccountSerializer(bindings, many=True)
        return APIResponse.success(serializer.data)
    
    @action(detail=False, methods=['post'])
    def batch_add(self, request):
        """批量添加账号到模型"""
        serializer = ModelUpstreamAccountCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.error(str(serializer.errors), 400)
        
        model_id = request.data.get('model_id')
        account_ids = serializer.validated_data['account_ids']
        weight = serializer.validated_data['weight']
        
        try:
            model = AIModel.objects.get(pk=model_id)
        except AIModel.DoesNotExist:
            return APIResponse.error('模型不存在', 404)
        
        created = []
        for account_id in account_ids:
            binding, is_new = ModelUpstreamAccount.objects.get_or_create(
                model=model,
                account_id=account_id,
                defaults={'weight': weight, 'is_enabled': True}
            )
            if is_new:
                created.append(binding)
        
        return APIResponse.success({
            'created': len(created),
            'total': len(account_ids)
        }, f'成功添加 {len(created)} 个账号')
    
    @action(detail=False, methods=['delete'])
    def batch_remove(self, request):
        """批量移除模型账号"""
        binding_ids = request.data.get('binding_ids', [])
        deleted, _ = ModelUpstreamAccount.objects.filter(id__in=binding_ids).delete()
        return APIResponse.success({'deleted': deleted}, f'已移除 {deleted} 个账号')
    
    @action(detail=True, methods=['patch'])
    def update_weight(self, request, pk=None):
        """更新账号权重"""
        binding = self.get_object()
        weight = request.data.get('weight', 1)
        binding.weight = max(1, min(100, weight))
        binding.save()
        return APIResponse.success({'weight': binding.weight})
    
    @action(detail=True, methods=['post'])
    def toggle(self, request, pk=None):
        """启用/禁用账号"""
        binding = self.get_object()
        binding.is_enabled = not binding.is_enabled
        binding.save()
        return APIResponse.success({
            'is_enabled': binding.is_enabled,
            'message': f'已{"启用" if binding.is_enabled else "禁用"}'
        })
    
    @action(detail=False, methods=['get'], url_path='select/(?P<model_id>[^/.]+)')
    def select_account(self, request, model_id=None):
        """选择可用账号（负载均衡）"""
        bindings = self.get_queryset().filter(
            model_id=model_id,
            is_enabled=True,
            account__is_active=True,
            account__is_available=True
        )
        
        if not bindings.exists():
            return APIResponse.error('没有可用的上游账号', 400)
        
        # 加权随机选择
        total_weight = sum(b.weight for b in bindings)
        rand_val = random.randint(1, total_weight)
        
        cumsum = 0
        selected = None
        for binding in bindings:
            cumsum += binding.weight
            if rand_val <= cumsum:
                selected = binding
                break
        
        if not selected:
            selected = bindings.first()
        
        # 更新使用统计
        selected.usage_count += 1
        selected.last_used = timezone.now()
        selected.save()
        
        return APIResponse.success({
            'account_id': selected.account.id,
            'name': selected.account.name,
            'base_url': selected.account.base_url,
            'api_key': selected.account.api_key,
            'proxy_url': selected.account.proxy_url
        })
