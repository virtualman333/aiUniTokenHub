import uuid
from django.db import models
from django.conf import settings


def image_upload_path(instance, filename):
    """生成图片上传路径: media/image_gen/user_{id}/{uuid}.png"""
    ext = filename.split('.')[-1] if '.' in filename else 'png'
    user_id = instance.generation.user_id
    return f'image_gen/user_{user_id}/{uuid.uuid4().hex}.{ext}'


class ImageGeneration(models.Model):
    """图像生成记录"""

    STATUS_CHOICES = [
        ('pending', '生成中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='image_generations', verbose_name='用户')
    model_code = models.CharField('模型代码', max_length=100, default='gpt-image-2')
    mode = models.CharField('模式', max_length=20, choices=[
        ('generate', '生成'), ('edit', '编辑'),
    ], default='generate')
    prompt = models.TextField('提示词')
    size = models.CharField('尺寸', max_length=20, default='auto')
    quality = models.CharField('质量', max_length=20, default='auto')
    n = models.IntegerField('生成数量', default=1)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField('错误信息', blank=True, default='')
    cost = models.DecimalField('费用(元)', max_digits=10, decimal_places=4, default=0)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'image_generations'
        verbose_name = '图像生成记录'
        verbose_name_plural = '图像生成记录'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} - {self.model_code} - {self.created_at}'


class GeneratedImage(models.Model):
    """生成的图片"""
    generation = models.ForeignKey(
        ImageGeneration, on_delete=models.CASCADE,
        related_name='images', verbose_name='生成记录')
    image = models.ImageField('图片', upload_to=image_upload_path)
    revised_prompt = models.TextField('修改后的提示词', blank=True, default='')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'generated_images'
        verbose_name = '生成图片'
        verbose_name_plural = '生成图片'
        ordering = ['id']

    def __str__(self):
        return f'Image #{self.id} of Generation #{self.generation_id}'
