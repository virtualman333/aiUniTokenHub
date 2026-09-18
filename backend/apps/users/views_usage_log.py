# -*- coding: utf-8 -*-
"""用户侧「我的调用记录」视图。

这个文件原来叫 `views_api_key.py`，里面躺着两个类：`UserAPIKeyViewSet` 和
`APIAccessLogViewSet`。前者**从未被注册过** —— `git log -S UserAPIKeyViewSet`
只有初次提交那一条，`urls.py` 里始终没出现过它；`/api/users/keys/` 一直是
`apps/users/views.py::APIKeyViewSet` 在服务（`MyKeys/composables/useMyKeys.ts`
打的正是这个地址）。两份实现也已经漂了：被注册的那份走 `APIResponse` 信封，
没被注册的那份直接 `return Response({...})`，创建密钥时把完整密钥塞在顶层。

留着它的唯一后果，是下一个人改「API 密钥那个 viewset」时可能改到死的那一份 ——
所以第 23 轮把它删掉，文件名也改成与剩下内容相符的名字。
"""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.api_proxy.models import APIAccessLog
from apps.api_proxy.serializers import APIAccessLogSerializer
from apps.utils.pagination import paginate
from apps.utils.response import APIResponse


class APIAccessLogViewSet(viewsets.ReadOnlyModelViewSet):
    """API 接口使用记录（用户侧）—— 只看得见自己的。"""

    serializer_class = APIAccessLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = APIAccessLog.objects.filter(user=self.request.user)
        # 支持状态过滤
        status = self.request.query_params.get('status')
        if status == 'success':
            queryset = queryset.filter(response_status__gte=200, response_status__lt=300)
        elif status == 'error':
            queryset = queryset.filter(response_status__gte=400)
        return queryset.order_by('-created_at')

    def list(self, request, *args, **kwargs):
        """分页列表。

        原来这里没重写，走的是 DRF 默认实现：裸数组、没有 `total`、也没有 `page_size`
        上限 —— 前端只能写 `res.results || res || []` 去猜这次拿到的是哪种形状。
        `settings.REST_FRAMEWORK['PAGE_SIZE']` 那句「死配置」正是这么被漏过去的：
        它只在配了 `DEFAULT_PAGINATION_CLASS` 时才生效，而本仓一个分页类都没配。
        """
        return paginate(request, self.get_queryset(), self.get_serializer, '获取成功')

    def retrieve(self, request, *args, **kwargs):
        """单条也收进信封 —— 同一个端点的两种形状不该各走各的。"""
        instance = self.get_object()
        return APIResponse.success(self.get_serializer(instance).data, '获取成功')
