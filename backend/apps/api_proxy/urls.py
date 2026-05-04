from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import APICategoryViewSet, APIEndpointViewSet, ProxyAccessViewSet
from .views_openai import OpenAIProxyView, models_list, StreamProxyView

router = DefaultRouter()
router.register(r'categories', APICategoryViewSet, basename='categories')
router.register(r'endpoints', APIEndpointViewSet, basename='endpoints')
router.register(r'forward', ProxyAccessViewSet, basename='forward')

urlpatterns = [
    # OpenAI兼容格式路由
    path('v1/chat/completions', OpenAIProxyView.as_view(), name='openai-chat'),
    path('v1/completions', OpenAIProxyView.as_view(), name='openai-completions'),
    path('v1/embeddings', OpenAIProxyView.as_view(), name='openai-embeddings'),
    path('v1/images/generations', OpenAIProxyView.as_view(), name='openai-images'),
    path('v1/audio/transcriptions', OpenAIProxyView.as_view(), name='openai-audio'),
    path('v1/models', models_list, name='openai-models'),
    path('v1/stream/<path:path>', StreamProxyView.as_view(), name='openai-stream'),
    path('<path:path>', OpenAIProxyView.as_view(), name='openai-generic'),
    
    # 标准路由
    path('', include(router.urls)),
]
