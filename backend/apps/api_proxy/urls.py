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
]
