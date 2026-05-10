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
from apps.api_proxy.channel_probes import fetch_models, probe_status


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
        
        try:
            added_count, bound_count = self._fetch_and_add_models(instance)
        except Exception as e:
            # 认证失败等错误：账号已创建但同步失败，返回警告
            instance.is_available = False
            instance.last_error = str(e)[:500]
            instance.save(update_fields=['is_available', 'last_error'])
            return APIResponse.created(
                {**serializer.data, 'models_added': 0, 'accounts_bound': 0},
                f'账号已创建，但同步模型失败: {str(e)[:200]}'
            )
        
        return APIResponse.created(
            {**serializer.data, 'models_added': added_count, 'accounts_bound': bound_count},
            f'创建成功，已添加 {added_count} 个模型并绑定 {bound_count} 个账号'
        )
    
    def _fetch_and_add_models(self, account):
        """从上游获取模型列表并添加到数据库，返回元组(新增模型数, 绑定数)"""
        try:
            models_data = fetch_models(account, timeout=15)
            base_url = account.base_url.rstrip('/')
            
            if not models_data:
                return (0, 0)
            
            # 获取或创建供应商
            provider = self._get_or_create_provider(base_url, account)
            
            # 更新账号的供应商（如果未设置）
            if not account.provider_id:
                account.provider = provider
                account.save(update_fields=['provider'])
            
            added_count = 0
            bound_count = 0  # 新绑定数量
            for model_info in models_data:
                model_id = model_info.get('id', '')
                if not model_id:
                    continue
                display_name = model_info.get('display_name') or model_id
                
                # 获取或创建模型
                model, created = AIModel.objects.get_or_create(
                    code=model_id,
                    defaults={
                        'name': display_name,
                        'provider': provider,
                        'status': 'active',  # 新同步的模型默认启用
                        'description': '可用' if model_info.get('ready', True) else '未知',
                    }
                )
                
                if created:
                    added_count += 1
                
                # 自动将账号绑定到模型
                binding, is_new = ModelUpstreamAccount.objects.get_or_create(
                    model=model,
                    account=account,
                    defaults={'weight': 1, 'is_enabled': True}
                )
                if is_new:
                    bound_count += 1
            
            # 更新账号状态
            account.is_available = True
            account.last_error = ''
            account.save(update_fields=['is_available', 'last_error'])
            
            return (added_count, bound_count)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            # 认证错误必须向上抛出，不能静默吞掉
            if hasattr(e, 'response') and getattr(e.response, 'status_code', None) in (401, 403):
                raise
            # 其他错误不影响账号创建，记录但不中断
            return (0, 0)
    
    def _get_or_create_provider(self, base_url, account):
        """根据base_url获取或创建供应商"""
        # 如果账号已有供应商，直接返回
        if account.provider_id:
            return account.provider
        
        # 从base_url提取供应商标识
        provider_mapping = {
            'openai': 'OpenAI',
            'anthropic': 'Anthropic',
            'deepseek': 'DeepSeek',
            'zhipu': '智谱AI',
            'baidu': '百度AI',
            'aliyun': '阿里云',
            'ali': '阿里云',
            'moonshot': '月之暗面',
            'minimax': 'MiniMax',
            'gemini': 'Google Gemini',
            'ollama': 'Ollama',
            'localai': 'LocalAI',
            'together': 'Together AI',
            'groq': 'Groq',
            'mistral': 'Mistral',
            'cohere': 'Cohere',
        }
        
        base_url_lower = base_url.lower()
        provider_code = 'custom'
        provider_name = 'Custom'
        
        for key, name in provider_mapping.items():
            if key in base_url_lower:
                provider_code = key if key not in ['ali'] else 'aliyun'
                provider_name = name
                break
        
        provider, created = ModelProvider.objects.get_or_create(
            code=provider_code,
            defaults={
                'name': provider_name,
                'is_active': True,
            }
        )
        
        if created:
            print(f"自动创建供应商: {provider_code} - {provider_name}")
        
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
            ok, error = probe_status(account, timeout=10)
            if ok:
                account.is_available = True
                account.last_error = ''
                account.save()
                return APIResponse.success({'status': 'ok'}, '连接成功')
            else:
                account.is_available = False
                account.last_error = error
                account.save()
                return APIResponse.error(f'连接失败: {error}', 400)
        except Exception as e:
            account.is_available = False
            account.last_error = str(e)[:500]
            account.save()
            return APIResponse.error(f'连接失败: {str(e)}', 400)
    
    @action(detail=True, methods=['post'])
    def sync_models(self, request, pk=None):
        """从上游账号同步模型列表"""
        account = self.get_object()
        try:
            added_count, bound_count = self._fetch_and_add_models(account)
            return APIResponse.success(
                {'added': added_count, 'bound': bound_count},
                f'成功同步 {added_count} 个模型，绑定 {bound_count} 个账号'
            )
        except Exception as e:
            error_msg = str(e)[:500]
            account.is_available = False
            account.last_error = error_msg
            account.save(update_fields=['is_available', 'last_error'])
            return APIResponse.error(f'同步失败: {error_msg}', 400)

    @action(detail=True, methods=['get'])
    def model_list(self, request, pk=None):
        """获取该账号绑定的模型列表"""
        account = self.get_object()
        bindings = ModelUpstreamAccount.objects.filter(
            account=account, is_enabled=True
        ).select_related('model')
        model_list = []
        for binding in bindings:
            model = binding.model
            model_list.append({
                'id': model.id,
                'name': model.name,
                'code': model.code,
                'status': model.status,
                'provider_name': model.provider.name if model.provider else '',
                'input_price': float(model.input_price) if model.input_price else 0,
                'output_price': float(model.output_price) if model.output_price else 0,
                'binding_id': binding.id,
                'weight': binding.weight,
                'usage_count': binding.usage_count,
            })
        return APIResponse.success(model_list, '获取成功')


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
            'protocol': selected.account.protocol,
            'base_url': selected.account.base_url,
            'api_key': selected.account.api_key,
            'proxy_url': selected.account.proxy_url
        })
