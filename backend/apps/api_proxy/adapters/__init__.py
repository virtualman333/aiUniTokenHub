"""
OpenAI Response API ↔ Chat Completions API 适配器模块
"""
from .request_adapter import convert_request
from .response_adapter import convert_response
from .streaming_adapter import StreamingConverter

__all__ = [
    'convert_request',
    'convert_response',
    'StreamingConverter',
]
