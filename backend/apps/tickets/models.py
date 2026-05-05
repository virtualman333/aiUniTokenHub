import os
import uuid
from django.db import models
from django.conf import settings


def ticket_image_upload_path(instance, filename):
    """生成工单图片上传路径"""
    ext = os.path.splitext(filename)[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    return f"tickets/{instance.ticket_id}/{filename}"


class TicketCategory(models.Model):
    """工单分类"""
    name = models.CharField('分类名称', max_length=50, unique=True)
    code = models.CharField('分类代码', max_length=20, unique=True)
    description = models.CharField('分类描述', max_length=200, blank=True)
    sort_order = models.IntegerField('排序', default=0)
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'ticket_categories'
        verbose_name = '工单分类'
        verbose_name_plural = '工单分类'
        ordering = ('sort_order', '-created_at')

    def __str__(self):
        return self.name


class Ticket(models.Model):
    """工单"""
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('resolved', '已解决'),
    ]
    PRIORITY_CHOICES = [
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('urgent', '紧急'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='tickets', verbose_name='用户'
    )
    category = models.ForeignKey(
        TicketCategory, on_delete=models.SET_NULL, null=True,
        related_name='tickets', verbose_name='分类'
    )
    title = models.CharField('工单标题', max_length=200)
    content = models.TextField('工单内容')
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField('优先级', max_length=20, choices=PRIORITY_CHOICES, default='medium')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_tickets', verbose_name='处理人'
    )
    resolved_at = models.DateTimeField('解决时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'tickets'
        verbose_name = '工单'
        verbose_name_plural = '工单'
        ordering = ('-created_at',)

    def __str__(self):
        return f"[{self.get_status_display()}] {self.title}"


class TicketReply(models.Model):
    """工单回复"""
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE,
        related_name='replies', verbose_name='工单'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='ticket_replies', verbose_name='回复人'
    )
    content = models.TextField('回复内容')
    is_staff_reply = models.BooleanField('是否管理员回复', default=False)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'ticket_replies'
        verbose_name = '工单回复'
        verbose_name_plural = '工单回复'
        ordering = ('created_at',)

    def __str__(self):
        return f"回复 #{self.ticket_id} by {self.user.username}"


class TicketImage(models.Model):
    """工单图片"""
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE,
        related_name='images', verbose_name='工单',
        null=True, blank=True
    )
    reply = models.ForeignKey(
        TicketReply, on_delete=models.CASCADE,
        related_name='images', verbose_name='回复',
        null=True, blank=True
    )
    image = models.ImageField('图片', upload_to=ticket_image_upload_path)
    original_name = models.CharField('原始文件名', max_length=255)
    file_size = models.IntegerField('文件大小(字节)', default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'ticket_images'
        verbose_name = '工单图片'
        verbose_name_plural = '工单图片'
        ordering = ('created_at',)

    def __str__(self):
        return f"图片 #{self.id} - {self.original_name}"

    @property
    def url(self):
        if self.image:
            return self.image.url
        return None
