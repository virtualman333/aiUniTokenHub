"""
对话会话 / 消息相关接口
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction

from apps.utils.response import APIResponse
from .models import Conversation, ChatMessage


# ============== 序列化辅助 ==============

def serialize_message(m: ChatMessage) -> dict:
    return {
        'id': m.id,
        'role': m.role,
        'content': m.content,
        'model_code': m.model_code,
        'prompt_tokens': m.prompt_tokens,
        'completion_tokens': m.completion_tokens,
        'total_tokens': m.total_tokens,
        'usage_details': m.usage_details or {},
        'created_at': m.created_at.isoformat() if m.created_at else None,
    }


def serialize_conversation(c: Conversation, last_msg: str = '') -> dict:
    return {
        'id': c.id,
        'title': c.title,
        'model_code': c.model_code,
        'system_prompt': c.system_prompt,
        'is_pinned': c.is_pinned,
        'last_message_at': c.last_message_at.isoformat() if c.last_message_at else None,
        'created_at': c.created_at.isoformat() if c.created_at else None,
        'last_message': last_msg,
        'message_count': c.messages.count(),
    }


# ============== ViewSet ==============

class ConversationViewSet(viewsets.GenericViewSet):
    """
    对话会话管理
    - GET    /conversations/                   列表
    - POST   /conversations/                   创建
    - GET    /conversations/{id}/              详情（含消息）
    - PATCH  /conversations/{id}/              更新（标题/置顶/system_prompt）
    - DELETE /conversations/{id}/              删除
    - POST   /conversations/{id}/clear/        清空消息
    - GET    /conversations/{id}/messages/     消息列表
    - POST   /conversations/{id}/messages/     新增消息
    """
    permission_classes = [IsAuthenticated]

    def _get_obj(self, request, pk):
        return get_object_or_404(Conversation, pk=pk, user=request.user)

    # ---------- 集合 ----------
    def list(self, request):
        qs = Conversation.objects.filter(user=request.user)
        data = []
        for c in qs:
            last = c.messages.order_by('-created_at', '-id').first()
            last_msg_preview = ''
            if last:
                last_msg_preview = (last.content or '')[:80]
            data.append(serialize_conversation(c, last_msg_preview))
        return APIResponse.success(data)

    def create(self, request):
        title = (request.data.get('title') or '新对话').strip()[:200]
        model_code = (request.data.get('model_code') or '').strip()[:128]
        system_prompt = request.data.get('system_prompt') or ''
        c = Conversation.objects.create(
            user=request.user,
            title=title,
            model_code=model_code,
            system_prompt=system_prompt,
        )
        return APIResponse.created(serialize_conversation(c))

    # ---------- 单体 ----------
    def retrieve(self, request, pk=None):
        c = self._get_obj(request, pk)
        msgs = [serialize_message(m) for m in c.messages.all()]
        data = serialize_conversation(c)
        data['messages'] = msgs
        return APIResponse.success(data)

    def partial_update(self, request, pk=None):
        c = self._get_obj(request, pk)
        if 'title' in request.data:
            c.title = (request.data.get('title') or '').strip()[:200] or c.title
        if 'is_pinned' in request.data:
            c.is_pinned = bool(request.data.get('is_pinned'))
        if 'model_code' in request.data:
            c.model_code = (request.data.get('model_code') or '').strip()[:128]
        if 'system_prompt' in request.data:
            c.system_prompt = request.data.get('system_prompt') or ''
        c.save()
        return APIResponse.success(serialize_conversation(c))

    def destroy(self, request, pk=None):
        c = self._get_obj(request, pk)
        c.delete()
        return APIResponse.success(msg='已删除')

    # ---------- 自定义动作 ----------
    @action(detail=True, methods=['post'])
    def clear(self, request, pk=None):
        """清空当前会话所有消息"""
        c = self._get_obj(request, pk)
        c.messages.all().delete()
        return APIResponse.success(msg='已清空')

    @action(detail=True, methods=['get', 'post'], url_path='messages')
    def messages(self, request, pk=None):
        """会话下消息的获取/新增"""
        c = self._get_obj(request, pk)
        if request.method == 'GET':
            data = [serialize_message(m) for m in c.messages.all()]
            return APIResponse.success(data)

        # POST 新增
        role = request.data.get('role')
        content = request.data.get('content', '')
        model_code = request.data.get('model_code', '') or c.model_code
        if role not in ('system', 'user', 'assistant'):
            return APIResponse.error('role 非法', 400)
        with transaction.atomic():
            usage_details = request.data.get('usage_details') or {}
            if not isinstance(usage_details, dict):
                usage_details = {}
            m = ChatMessage.objects.create(
                conversation=c,
                role=role,
                content=content,
                model_code=model_code,
                prompt_tokens=int(request.data.get('prompt_tokens') or 0),
                completion_tokens=int(request.data.get('completion_tokens') or 0),
                total_tokens=int(request.data.get('total_tokens') or 0),
                usage_details=usage_details,
            )
            # 更新会话标题（首次用户消息时自动取前 30 字作为标题）
            if c.title in ('新对话', '', None) and role == 'user' and content:
                c.title = content.strip().splitlines()[0][:30]
            c.save()
        return APIResponse.created(serialize_message(m))

    @action(detail=True, methods=['delete'], url_path=r'messages/(?P<msg_id>[0-9]+)')
    def delete_message(self, request, pk=None, msg_id=None):
        """删除某条消息"""
        c = self._get_obj(request, pk)
        ChatMessage.objects.filter(conversation=c, pk=msg_id).delete()
        return APIResponse.success(msg='已删除')
