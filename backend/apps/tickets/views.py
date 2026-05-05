from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils import timezone
from .models import TicketCategory, Ticket, TicketReply, TicketImage
from .serializers import (
    TicketCategorySerializer, TicketListSerializer, TicketDetailSerializer,
    TicketCreateSerializer, TicketUpdateSerializer, TicketReplySerializer,
    TicketImageSerializer
)
from apps.utils.response import APIResponse


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
            errors = serializer.errors
            first_error = list(errors.values())[0][0] if errors else '参数错误'
            return APIResponse.error(str(first_error), 400)
        serializer.save()
        return APIResponse.created(serializer.data, '创建成功')

    def update(self, request, pk=None):
        if not request.user.is_staff:
            return APIResponse.error('无权限', 403)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if not serializer.is_valid():
            errors = serializer.errors
            first_error = list(errors.values())[0][0] if errors else '参数错误'
            return APIResponse.error(str(first_error), 400)
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
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            errors = serializer.errors
            first_error = list(errors.values())[0][0] if errors else '参数错误'
            return APIResponse.error(str(first_error), 400)
        ticket = serializer.save(user=request.user)
        # 处理图片ID关联
        image_ids = request.data.get('image_ids', [])
        if image_ids:
            if len(image_ids) > 5:
                return APIResponse.error('最多关联5张图片', 400)
            # 更新已上传图片的ticket关联
            TicketImage.objects.filter(id__in=image_ids, ticket__isnull=True).update(ticket=ticket)
        return APIResponse.created(TicketDetailSerializer(ticket, context={'request': request}).data, '工单创建成功')

    def retrieve(self, request, pk=None):
        instance = self.get_object()
        if not request.user.is_staff and instance.user != request.user:
            return APIResponse.error('无权限', 403)
        serializer = self.get_serializer(instance)
        return APIResponse.success(serializer.data, '获取成功')

    def update(self, request, pk=None):
        if not request.user.is_staff:
            return APIResponse.error('无权限', 403)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if not serializer.is_valid():
            errors = serializer.errors
            first_error = list(errors.values())[0][0] if errors else '参数错误'
            return APIResponse.error(str(first_error), 400)
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
        content = request.data.get('content')
        if not content or len(content.strip()) < 2:
            return APIResponse.error('回复内容至少2个字符', 400)
        reply = TicketReply.objects.create(
            ticket=instance,
            user=request.user,
            content=content.strip(),
            is_staff_reply=request.user.is_staff
        )
        # 处理图片ID关联
        image_ids = request.data.get('image_ids', [])
        if image_ids:
            if len(image_ids) > 5:
                return APIResponse.error('最多关联5张图片', 400)
            # 更新已上传图片的reply关联
            TicketImage.objects.filter(id__in=image_ids, reply__isnull=True, ticket__isnull=True).update(reply=reply)
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
        if image.size > 5 * 1024 * 1024:  # 5MB
            return APIResponse.error('图片大小不能超过5MB', 400)
        # 检查文件类型
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if image.content_type not in allowed_types:
            return APIResponse.error('只支持 JPG、PNG、GIF、WebP 格式的图片', 400)
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
