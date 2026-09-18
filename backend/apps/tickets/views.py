from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db import transaction
from django.utils import timezone
from .models import TicketCategory, Ticket, TicketReply, TicketImage
from .serializers import (
    TicketCategorySerializer, TicketListSerializer, TicketDetailSerializer,
    TicketCreateSerializer, TicketUpdateSerializer, TicketReplySerializer,
    TicketImageSerializer
)
from .attachments import (
    ALLOWED_IMAGE_TYPES, MAX_IMAGE_BYTES,
    allowed_types_message, max_size_message, parse_image_ids, partial_binding_error,
)
from apps.utils.response import APIResponse
from apps.utils.api_errors import first_error_message


def _bind_images(image_ids, *, ticket=None, reply=None):
    """把一组「还没归属」的图片挂到工单或回复上，返回没绑满时的那句话。

    筛选条件写在这里而不是各处一遍：两条入口（建工单 / 回复）的规矩是同一个
    ——**一张图只能有一个去处**。从前 ticket 那条路径只判 `ticket__isnull`，
    于是一张已经挂在回复上的图还能再被挂到一个工单上。

    返回值必须被调用方拿去判断：`update()` 影响 0 行也是「成功」，不看返回值
    就等于允许「提交成功但一张图都没带上」。
    """
    if not image_ids:
        return None
    queryset = TicketImage.objects.filter(
        id__in=image_ids, ticket__isnull=True, reply__isnull=True
    )
    if ticket is not None:
        bound = queryset.update(ticket=ticket)
    else:
        bound = queryset.update(reply=reply)
    return partial_binding_error(len(image_ids), bound)


class TicketCategoryViewSet(viewsets.ModelViewSet):
    """工单分类管理"""
    serializer_class = TicketCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return TicketCategory.objects.all()
        return TicketCategory.objects.filter(is_active=True)

    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return APIResponse.success(serializer.data, '获取成功')

    def create(self, request):
        if not request.user.is_staff:
            return APIResponse.error('无权限', 403)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.error(first_error_message(serializer.errors), 400)
        serializer.save()
        return APIResponse.created(serializer.data, '创建成功')

    def update(self, request, pk=None):
        if not request.user.is_staff:
            return APIResponse.error('无权限', 403)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if not serializer.is_valid():
            return APIResponse.error(first_error_message(serializer.errors), 400)
        serializer.save()
        return APIResponse.success(serializer.data, '更新成功')

    def destroy(self, request, pk=None):
        if not request.user.is_staff:
            return APIResponse.error('无权限', 403)
        instance = self.get_object()
        if instance.tickets.exists():
            return APIResponse.error('该分类下存在工单，无法删除', 400)
        instance.delete()
        return APIResponse.success(None, '删除成功')


class TicketViewSet(viewsets.ModelViewSet):
    """工单管理"""
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return TicketCreateSerializer
        if self.action in ['update', 'partial_update']:
            return TicketUpdateSerializer
        if self.action == 'retrieve':
            return TicketDetailSerializer
        return TicketListSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Ticket.objects.select_related('user', 'category', 'assigned_to')
        if user.is_staff:
            status_filter = self.request.query_params.get('status')
            category_filter = self.request.query_params.get('category')
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            if category_filter:
                queryset = queryset.filter(category_id=category_filter)
        else:
            queryset = queryset.filter(user=user)
        return queryset

    def list(self, request):
        queryset = self.get_queryset()
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        tickets = queryset[start:end]
        serializer = self.get_serializer(tickets, many=True)
        return APIResponse.paginated(serializer.data, total, page, page_size)

    def create(self, request):
        # 图片 id 先收先判 —— 从前这一步排在 serializer.save() 的后面，
        # 于是那句「最多关联 5 张」的 400 里夹着一条**已经落库**的工单。
        image_ids, error = parse_image_ids(request.data.get('image_ids'))
        if error:
            return APIResponse.error(error, 400)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.error(first_error_message(serializer.errors), 400)
        # 建工单与绑图要么都成、要么都不成：绑不满就整笔回滚，
        # 而不是收下一张「提交成功但没有图」的工单。
        with transaction.atomic():
            ticket = serializer.save(user=request.user)
            error = _bind_images(image_ids, ticket=ticket)
            if error:
                transaction.set_rollback(True)
                return APIResponse.error(error, 400)
        return APIResponse.created(TicketDetailSerializer(ticket, context={'request': request}).data, '工单创建成功')

    def retrieve(self, request, pk=None):
        instance = self.get_object()
        if not request.user.is_staff and instance.user != request.user:
            return APIResponse.error('无权限', 403)
        serializer = self.get_serializer(instance)
        return APIResponse.success(serializer.data, '获取成功')

    def update(self, request, pk=None):
        """完整更新工单（管理员）"""
        if not request.user.is_staff:
            return APIResponse.error('无权限', 403)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if not serializer.is_valid():
            return APIResponse.error(first_error_message(serializer.errors), 400)
        validated_data = serializer.validated_data
        if 'status' in validated_data and validated_data['status'] == 'resolved':
            instance.resolved_at = timezone.now()
        serializer.save()
        return APIResponse.success(serializer.data, '更新成功')

    def partial_update(self, request, pk=None):
        """部分更新工单（管理员）"""
        if not request.user.is_staff:
            return APIResponse.error('无权限', 403)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if not serializer.is_valid():
            return APIResponse.error(first_error_message(serializer.errors), 400)
        validated_data = serializer.validated_data
        if 'status' in validated_data and validated_data['status'] == 'resolved':
            instance.resolved_at = timezone.now()
        serializer.save()
        return APIResponse.success(serializer.data, '更新成功')

    @action(detail=True, methods=['post'])
    def reply(self, request, pk=None):
        """回复工单"""
        instance = self.get_object()
        if not request.user.is_staff and instance.user != request.user:
            return APIResponse.error('无权限', 403)
        # 与建工单同一条规矩：先校验，再写库。
        image_ids, error = parse_image_ids(request.data.get('image_ids'))
        if error:
            return APIResponse.error(error, 400)
        content = request.data.get('content')
        if not content or len(content.strip()) < 2:
            return APIResponse.error('回复内容至少2个字符', 400)
        with transaction.atomic():
            reply = TicketReply.objects.create(
                ticket=instance,
                user=request.user,
                content=content.strip(),
                is_staff_reply=request.user.is_staff
            )
            error = _bind_images(image_ids, reply=reply)
            if error:
                transaction.set_rollback(True)
                return APIResponse.error(error, 400)
            if request.user.is_staff and instance.status == 'pending':
                instance.status = 'processing'
                instance.assigned_to = request.user
                instance.save()
        return APIResponse.created(TicketReplySerializer(reply, context={'request': request}).data, '回复成功')

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """工单统计（管理员）"""
        if not request.user.is_staff:
            return APIResponse.error('无权限', 403)
        total = Ticket.objects.count()
        pending = Ticket.objects.filter(status='pending').count()
        processing = Ticket.objects.filter(status='processing').count()
        resolved = Ticket.objects.filter(status='resolved').count()
        return APIResponse.success({
            'total': total,
            'pending': pending,
            'processing': processing,
            'resolved': resolved
        }, '获取成功')

    @action(detail=False, methods=['post'], url_path='upload-image')
    def upload_image(self, request):
        """上传工单图片"""
        image = request.FILES.get('image')
        if not image:
            return APIResponse.error('请选择图片', 400)
        # 上限与白名单都在 apps/tickets/attachments.py，提示语也由那张表生成 ——
        # 不会出现「拦得住 WebP、提示语里却没写」这种漂移。
        # 前端（ImageUpload.vue）有一份同样的白名单，两边的对账在
        # apps/tickets/tests/test_attachments.py 里。
        if image.size > MAX_IMAGE_BYTES:
            return APIResponse.error(max_size_message(), 400)
        if image.content_type not in ALLOWED_IMAGE_TYPES:
            return APIResponse.error(allowed_types_message(), 400)
        # 创建临时图片记录（ticket和reply为null）
        ticket_image = TicketImage.objects.create(
            image=image,
            original_name=image.name,
            file_size=image.size
        )
        return APIResponse.created(
            TicketImageSerializer(ticket_image, context={'request': request}).data,
            '图片上传成功'
        )
