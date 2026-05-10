# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_recharge_channel_package'),
    ]

    operations = [
        # 从渠道移除字段（如果之前添加过）
        migrations.RemoveField(
            model_name='rechargechannel',
            name='redirect_url',
        ),
        migrations.RemoveField(
            model_name='rechargechannel',
            name='callback_url',
        ),
        # 添加到套餐
        migrations.AddField(
            model_name='rechargepackage',
            name='redirect_url',
            field=models.URLField(
                blank=True,
                help_text='第三方充值网站跳转地址，如：https://xxx.com/pay?amount={amount}&order={order_id}',
                max_length=500,
                verbose_name='跳转URL'
            ),
        ),
        migrations.AddField(
            model_name='rechargepackage',
            name='callback_url',
            field=models.URLField(
                blank=True,
                help_text='第三方回调通知地址（可选）',
                max_length=500,
                verbose_name='回调URL'
            ),
        ),
    ]
