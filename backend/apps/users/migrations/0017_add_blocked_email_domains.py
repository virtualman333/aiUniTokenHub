# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0016_update_bonus_bill_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailconfig',
            name='blocked_email_domains',
            field=models.TextField(blank=True, default='', verbose_name='邮箱域名黑名单'),
        ),
    ]
