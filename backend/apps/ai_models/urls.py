from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AIModelViewSet, ModelProviderViewSet, ModelCategoryViewSet
from .upstream_views import UpstreamAccountViewSet, ModelUpstreamAccountViewSet

router = DefaultRouter()
router.register(r'models', AIModelViewSet, basename='aimodels')
router.register(r'providers', ModelProviderViewSet, basename='providers')
router.register(r'categories', ModelCategoryViewSet, basename='modelcategories')
router.register(r'upstream-accounts', UpstreamAccountViewSet, basename='upstream-accounts')

urlpatterns = [
    # 模型账号关联管理
    path('model-upstream/', ModelUpstreamAccountViewSet.as_view({
        'get': 'list_by_model',
        'post': 'batch_add',
        'delete': 'batch_remove',
    }), name='model-upstream-list'),
    path('model-upstream/<int:pk>/', ModelUpstreamAccountViewSet.as_view({
        'patch': 'update_weight',
        'post': 'toggle',
    }), name='model-upstream-detail'),
    # 账号选择（负载均衡）
    path('model-upstream/select/<int:model_id>/', ModelUpstreamAccountViewSet.as_view({
        'get': 'select_account',
    }), name='model-upstream-select'),
    
    path('', include(router.urls)),
]
