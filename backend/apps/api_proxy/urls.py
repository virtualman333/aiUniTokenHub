"""
OpenAI 兼容 API 路由配置
支持标准 OpenAI API 端点格式
"""
from django.urls import path, re_path
from .views_openai import (
    ChatCompletionsView,
    CompletionsView,
    EmbeddingsView,
    ModelsView,
    models_list,
    model_retrieve,
)
from .views import ProxyAccessViewSet

urlpatterns = [
    # OpenAI 兼容端点
    path('v1/chat/completions', ChatCompletionsView.as_view(), name='chat-completions'),
    path('v1/completions', CompletionsView.as_view(), name='completions'),
    path('v1/embeddings', EmbeddingsView.as_view(), name='embeddings'),
    
    # 模型相关
    path('v1/models', models_list, name='models-list'),
    re_path(r'^v1/models/(?P<model_id>[^/]+)$', model_retrieve, name='model-retrieve'),
    
    # 通用路由 - 捕获所有 /v1/* 请求
    path('v1/<path:path>', ModelsView.as_view(), name='v1-generic'),
    
    # 根路径
    path('', ModelsView.as_view(), name='api-root'),
    
    # 访问日志相关路由（与前端保持一致）
    path('forward/access_logs/', ProxyAccessViewSet.as_view({'get': 'access_logs'}), name='forward-access-logs'),
    path('access_logs/', ProxyAccessViewSet.as_view({'get': 'access_logs'}), name='access-logs'),
    path('access_stats/', ProxyAccessViewSet.as_view({'get': 'access_stats'}), name='access-stats'),
    path('access_logs/<int:pk>/', ProxyAccessViewSet.as_view({'get': 'access_log_detail'}), name='access-log-detail'),
]
