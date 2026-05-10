# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_add_page_view'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailconfig',
            name='alert_enabled',
            field=models.BooleanField(
                default=False,
                help_text='启用后当API调用返回非200状态码时发送告警邮件',
                verbose_name='启用接口异常告警',
            ),
        ),
        migrations.AddField(
            model_name='emailconfig',
            name='alert_emails',
            field=models.TextField(
                blank=True,
                default='',
                help_text='多个邮箱用英文逗号分隔',
                verbose_name='告警邮箱列表',
            ),
        ),
    ]
