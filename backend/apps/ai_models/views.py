from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from django.db.models import Q
from .models import AIModel, ModelProvider, ModelCategory
from .serializers import (
    AIModelListSerializer, AIModelDetailSerializer, AIModelCreateSerializer,
    ModelProviderSerializer, ModelCategorySerializer
)


class ModelProviderViewSet(viewsets.ModelViewSet):
    """供应商管理"""
    queryset = ModelProvider.objects.all()
    serializer_class = ModelProviderSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAdminUser()]
    
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
        
        # 非管理员只能看到已上架的
        if not self.request.user.is_authenticated or not getattr(self.request.user, 'role', None) == 'admin':
            queryset = queryset.filter(status='active')
        
        # 筛选参数
        provider = self.request.query_params.get('provider')
        category = self.request.query_params.get('category')
        status = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        featured = self.request.query_params.get('featured')
        
        if provider:
            queryset = queryset.filter(provider__code=provider)
        if category:
            queryset = queryset.filter(category__code=category)
        if status:
            queryset = queryset.filter(status=status)
        if featured == 'true':
            queryset = queryset.filter(is_featured=True)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(description__icontains=search) |
                Q(tags__icontains=search)
            )
        
        return queryset
    
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
