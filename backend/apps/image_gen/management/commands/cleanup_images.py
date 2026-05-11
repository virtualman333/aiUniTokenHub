import os
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.image_gen.models import ImageGeneration


class Command(BaseCommand):
    help = '清理超过5天的图像生成记录及其文件'

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=5)
        old_records = ImageGeneration.objects.filter(created_at__lt=cutoff)
        count = old_records.count()
        if count == 0:
            self.stdout.write('没有需要清理的记录')
            return
        # 删除关联图片文件
        for record in old_records:
            for img in record.images.all():
                if img.image:
                    try:
                        if os.path.isfile(img.image.path):
                            os.remove(img.image.path)
                    except Exception:
                        pass
        old_records.delete()
        self.stdout.write(self.style.SUCCESS(f'已清理 {count} 条图像生成记录'))
