from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from django.db.models import Q, Exists, OuterRef, Count
from .models import AIModel, ModelProvider, ModelCategory
from .serializers import (
    AIModelListSerializer, AIModelDetailSerializer, AIModelCreateSerializer,
    ModelProviderSerializer, ModelCategorySerializer
)
from .upstream_models import ModelUpstreamAccount
from apps.utils.response import APIResponse


class ModelProviderViewSet(viewsets.ModelViewSet):
    """供应商管理"""
    queryset = ModelProvider.objects.all()
    serializer_class = ModelProviderSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAdminUser()]
    
    def get_queryset(self):
        queryset = ModelProvider.objects.all()
        
        # 搜索
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(code__icontains=search) |
                Q(description__icontains=search)
            )
        
        # 状态过滤
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset.order_by('order', 'id')
    
    def list(self, request):
        queryset = self.get_queryset()
        
        # 分页
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        start = (page - 1) * page_size
        end = start + page_size
        
        total = queryset.count()
        items = queryset[start:end]
        
        serializer = self.get_serializer(items, many=True)
        return APIResponse.paginated(serializer.data, total, page, page_size, '获取成功')
    
    def retrieve(self, request, pk=None):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return APIResponse.success(serializer.data, '获取成功')
    
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            errors = serializer.errors
            first_error = list(errors.values())[0][0] if errors else '参数错误'
            return APIResponse.error(str(first_error), 400)
        self.perform_create(serializer)
        return APIResponse.created(serializer.data, '创建成功')
    
    def update(self, request, pk=None):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if not serializer.is_valid():
            errors = serializer.errors
            first_error = list(errors.values())[0][0] if errors else '参数错误'
            return APIResponse.error(str(first_error), 400)
        self.perform_update(serializer)
        return APIResponse.success(serializer.data, '更新成功')
    
    def partial_update(self, request, pk=None):
        return self.update(request, pk)
    
    def destroy(self, request, pk=None):
        instance = self.get_object()
        instance.delete()
        return APIResponse.success(None, '删除成功')
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """获取启用的供应商"""
        providers = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(providers, many=True)
        return Response(serializer.data)


class ModelCategoryViewSet(viewsets.ModelViewSet):
    """分类管理"""
    queryset = ModelCategory.objects.all()
    serializer_class = ModelCategorySerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAdminUser()]
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """获取启用的分类"""
        categories = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(categories, many=True)
        return Response(serializer.data)


class AIModelViewSet(viewsets.ModelViewSet):
    """AI模型管理"""
    queryset = AIModel.objects.all()
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AIModelCreateSerializer
        elif self.action == 'retrieve':
            return AIModelDetailSerializer
        return AIModelListSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'search', 'filters']:
            return [AllowAny()]
        return [IsAdminUser()]
    
    def get_queryset(self):
        queryset = AIModel.objects.select_related('provider', 'category')
        
        # 检查是否为管理员（支持 is_staff 或 role='admin'）
        user = self.request.user
        is_admin = (
            user.is_authenticated and (
                getattr(user, 'is_staff', False) or 
                getattr(user, 'role', None) == 'admin'
            )
        )
        
        # 非管理员只能看到已上架的
        if not is_admin:
            queryset = queryset.filter(status='active')
        
        # 使用 annotate 添加 has_accounts 和 account_count 字段（始终执行）
        # 统计启用的账号数量
        queryset = queryset.annotate(
            _account_count=Count(
                'upstream_accounts',
                filter=Q(upstream_accounts__is_enabled=True)
            )
        )
        
        # 筛选参数
        provider = self.request.query_params.get('provider')
        category = self.request.query_params.get('category')
        status = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        featured = self.request.query_params.get('featured')
        has_accounts = self.request.query_params.get('has_accounts')
        
        if provider:
            queryset = queryset.filter(provider__code=provider)
        if category:
            queryset = queryset.filter(category__code=category)
        if status:
            queryset = queryset.filter(status=status)
        if featured == 'true':
            queryset = queryset.filter(is_featured=True)
        if has_accounts == 'true':
            queryset = queryset.filter(_account_count__gt=0)
        elif has_accounts == 'false':
            queryset = queryset.filter(_account_count=0)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(description__icontains=search) |
                Q(tags__icontains=search)
            )
        
        return queryset.order_by('-is_featured', '-usage_count')
    
    def list(self, request):
        """获取模型列表"""
        queryset = self.get_queryset()
        
        # 分页
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        start = (page - 1) * page_size
        end = start + page_size
        
        total = queryset.count()
        items = queryset[start:end]
        
        serializer = self.get_serializer(items, many=True)
        return APIResponse.paginated(serializer.data, total, page, page_size, '获取成功')
    
    def retrieve(self, request, pk=None):
        """获取模型详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return APIResponse.success(serializer.data, '获取成功')
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """搜索模型"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def filters(self, request):
        """获取筛选选项"""
        providers = ModelProviderSerializer(
            ModelProvider.objects.filter(is_active=True), many=True
        ).data
        categories = ModelCategorySerializer(
            ModelCategory.objects.filter(is_active=True), many=True
        ).data
        
        return Response({
            'providers': providers,
            'categories': categories,
            'capabilities': [
                {'code': 'streaming', 'name': '流式输出'},
                {'code': 'vision', 'name': '视觉理解'},
                {'code': 'tools', 'name': '工具调用'},
                {'code': 'json', 'name': 'JSON模式'},
            ],
            'pricing_types': [
                {'code': 'free', 'name': '免费'},
                {'code': 'low', 'name': '低价'},
                {'code': 'normal', 'name': '标准'},
                {'code': 'high', 'name': '高价'},
            ]
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def toggle_status(self, request, pk=None):
        """切换上下架状态"""
        model = self.get_object()
        model.status = 'inactive' if model.status == 'active' else 'active'
        model.save()
        return Response({'status': model.status, 'message': '状态已更新'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def set_featured(self, request, pk=None):
        """设置推荐"""
        model = self.get_object()
        model.is_featured = request.data.get('featured', True)
        model.save()
        return Response({'is_featured': model.is_featured, 'message': '推荐状态已更新'})
    
    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def batch_delete(self, request):
        """批量删除模型"""
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'error': '请选择要删除的模型'}, status=status.HTTP_400_BAD_REQUEST)
        
        deleted_count, _ = AIModel.objects.filter(id__in=ids).delete()
        return Response({
            'deleted': deleted_count,
            'message': f'成功删除 {deleted_count} 个模型'
        })
    
    @action(detail=False, methods=['post'], permission_classes=[IsAdminUser])
    def batch_toggle_status(self, request):
        """批量切换上下架状态"""
        ids = request.data.get('ids', [])
        status_type = request.data.get('status')  # 'active' or 'inactive'
        
        if not ids:
            return Response({'error': '请选择要操作的模型'}, status=status.HTTP_400_BAD_REQUEST)
        
        if status_type not in ['active', 'inactive']:
            return Response({'error': '状态必须是 active 或 inactive'}, status=status.HTTP_400_BAD_REQUEST)
        
        updated_count = AIModel.objects.filter(id__in=ids).update(status=status_type)
        return Response({
            'updated': updated_count,
            'status': status_type,
            'message': f'成功更新 {updated_count} 个模型状态为 {status_type}'
        })
