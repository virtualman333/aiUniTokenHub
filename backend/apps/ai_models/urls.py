from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AIModelViewSet, ModelProviderViewSet, ModelCategoryViewSet
from .upstream_views import UpstreamAccountViewSet, ModelUpstreamAccountViewSet

router = DefaultRouter()
router.register(r'', AIModelViewSet, basename='aimodels')
router.register(r'providers', ModelProviderViewSet, basename='providers')
router.register(r'categories', ModelCategoryViewSet, basename='modelcategories')
router.register(r'upstream-accounts', UpstreamAccountViewSet, basename='upstream-accounts')

urlpatterns = [
    # 模型账号关联管理
    path('model-upstream/model/<int:model_id>/', ModelUpstreamAccountViewSet.as_view({
        'get': 'list_by_model',
    }), name='model-upstream-list'),
    path('model-upstream/batch-add/', ModelUpstreamAccountViewSet.as_view({
        'post': 'batch_add',
    }), name='model-upstream-batch-add'),
    path('model-upstream/batch-remove/', ModelUpstreamAccountViewSet.as_view({
        'delete': 'batch_remove',
    }), name='model-upstream-batch-remove'),
    path('model-upstream/<int:pk>/weight/', ModelUpstreamAccountViewSet.as_view({
        'patch': 'update_weight',
    }), name='model-upstream-weight'),
    path('model-upstream/<int:pk>/toggle/', ModelUpstreamAccountViewSet.as_view({
        'post': 'toggle',
    }), name='model-upstream-toggle'),
    path('model-upstream/select/<int:model_id>/', ModelUpstreamAccountViewSet.as_view({
        'get': 'select_account',
    }), name='model-upstream-select'),
    
    path('', include(router.urls)),
]
