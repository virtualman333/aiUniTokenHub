from rest_framework import serializers
from .models import TicketCategory, Ticket, TicketReply, TicketImage
from apps.users.serializers import UserSerializer


class TicketImageSerializer(serializers.ModelSerializer):
    """工单图片序列化器"""
    url = serializers.SerializerMethodField()

    class Meta:
        model = TicketImage
        fields = ['id', 'image', 'url', 'original_name', 'file_size', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class TicketCategorySerializer(serializers.ModelSerializer):
    """工单分类序列化器"""
    class Meta:
        model = TicketCategory
        fields = ['id', 'name', 'code', 'description', 'sort_order', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class TicketReplySerializer(serializers.ModelSerializer):
    """工单回复序列化器"""
    username = serializers.CharField(source='user.username', read_only=True)
    is_staff = serializers.BooleanField(source='user.is_staff', read_only=True)
    images = TicketImageSerializer(many=True, read_only=True)

    class Meta:
        model = TicketReply
        fields = ['id', 'ticket', 'user', 'username', 'is_staff', 'content', 'is_staff_reply', 'images', 'created_at']
        read_only_fields = ['id', 'user', 'is_staff_reply', 'created_at']


class TicketListSerializer(serializers.ModelSerializer):
    """工单列表序列化器"""
    username = serializers.CharField(source='user.username', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    reply_count = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = ['id', 'title', 'status', 'status_display', 'priority', 'priority_display',
                  'category', 'category_name', 'user', 'username', 'reply_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def get_reply_count(self, obj):
        return obj.replies.count()


class TicketDetailSerializer(serializers.ModelSerializer):
    """工单详情序列化器"""
    username = serializers.CharField(source='user.username', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)
    assigned_to_name = serializers.CharField(source='assigned_to.username', read_only=True, default=None)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    replies = TicketReplySerializer(many=True, read_only=True)
    images = TicketImageSerializer(many=True, read_only=True)

    class Meta:
        model = Ticket
        fields = ['id', 'title', 'content', 'status', 'status_display', 'priority', 'priority_display',
                  'category', 'category_name', 'user', 'username', 'assigned_to', 'assigned_to_name',
                  'resolved_at', 'replies', 'images', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'resolved_at', 'created_at', 'updated_at']


class TicketCreateSerializer(serializers.ModelSerializer):
    """创建工单序列化器"""
    class Meta:
        model = Ticket
        fields = ['title', 'content', 'category', 'priority']

    def validate_title(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError('工单标题至少2个字符')
        return value.strip()

    def validate_content(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError('工单内容至少5个字符')
        return value.strip()


class TicketUpdateSerializer(serializers.ModelSerializer):
    """更新工单序列化器（管理员）"""
    class Meta:
        model = Ticket
        fields = ['status', 'priority', 'assigned_to']

    def validate_status(self, value):
        if value not in dict(Ticket.STATUS_CHOICES):
            raise serializers.ValidationError('无效的状态')
        return value
