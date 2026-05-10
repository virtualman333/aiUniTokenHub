from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_add_token_cost_fields'),
    ]

    operations = [
        # 创建充值渠道模型
        migrations.CreateModel(
            name='RechargeChannel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='渠道名称')),
                ('code', models.CharField(max_length=50, unique=True, db_index=True, verbose_name='渠道代码')),
                ('description', models.CharField(max_length=500, blank=True, verbose_name='描述')),
                ('icon', models.CharField(max_length=255, blank=True, help_text='图标URL或CSS类名', verbose_name='图标')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
                ('sort_order', models.IntegerField(default=0, verbose_name='排序')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'verbose_name': '充值渠道',
                'verbose_name_plural': '充值渠道',
                'db_table': 'recharge_channels',
                'ordering': ('sort_order', '-created_at'),
            },
        ),
        # 创建充值套餐模型
        migrations.CreateModel(
            name='RechargePackage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='充值金额')),
                ('bonus', models.DecimalField(decimal_places=2, max_digits=10, default=0, help_text='赠送金额', verbose_name='赠送金额')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
                ('sort_order', models.IntegerField(default=0, verbose_name='排序')),
                ('description', models.CharField(max_length=500, blank=True, verbose_name='套餐说明')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('channel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='packages', to='users.rechargechannel', verbose_name='所属渠道')),
            ],
            options={
                'verbose_name': '充值套餐',
                'verbose_name_plural': '充值套餐',
                'db_table': 'recharge_packages',
                'ordering': ('sort_order', 'amount'),
            },
        ),
        # 为 CardPassword 添加 channel 外键
        migrations.AddField(
            model_name='cardpassword',
            name='channel',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='cards',
                to='users.rechargechannel',
                verbose_name='所属渠道'
            ),
        ),
        # 为 Bill 添加 channel 外键
        migrations.AddField(
            model_name='bill',
            name='channel',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='bills',
                to='users.rechargechannel',
                verbose_name='充值渠道'
            ),
        ),
    ]
