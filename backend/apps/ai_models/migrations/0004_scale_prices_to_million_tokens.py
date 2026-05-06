"""
数据迁移：把 AIModel.input_price / output_price 从 元/千tokens 转换为 元/百万tokens（×1000）。
仅一次性执行；reverse 时 ÷1000。
"""
from decimal import Decimal

from django.db import migrations


THOUSAND = Decimal('1000')


def scale_up(apps, schema_editor):
    AIModel = apps.get_model('ai_models', 'AIModel')
    for m in AIModel.objects.all():
        # 只对非 0 价格做转换；保留 cached_input_price 默认 0
        changed = False
        if m.input_price and m.input_price != 0:
            m.input_price = (m.input_price * THOUSAND).quantize(Decimal('0.0001'))
            changed = True
        if m.output_price and m.output_price != 0:
            m.output_price = (m.output_price * THOUSAND).quantize(Decimal('0.0001'))
            changed = True
        if changed:
            m.save(update_fields=['input_price', 'output_price'])


def scale_down(apps, schema_editor):
    AIModel = apps.get_model('ai_models', 'AIModel')
    for m in AIModel.objects.all():
        changed = False
        if m.input_price and m.input_price != 0:
            m.input_price = (m.input_price / THOUSAND).quantize(Decimal('0.000001'))
            changed = True
        if m.output_price and m.output_price != 0:
            m.output_price = (m.output_price / THOUSAND).quantize(Decimal('0.000001'))
            changed = True
        if changed:
            m.save(update_fields=['input_price', 'output_price'])


class Migration(migrations.Migration):

    dependencies = [
        ('ai_models', '0003_add_cached_input_price_and_unit'),
    ]

    operations = [
        migrations.RunPython(scale_up, reverse_code=scale_down),
    ]
