from django.db import migrations


def update_bonus_bills(apps, schema_editor):
    """将赠送相关的账单记录类型从 recharge 更新为 bonus"""
    Bill = apps.get_model('users', 'Bill')
    
    # 更新新用户注册赠送
    updated1 = Bill.objects.filter(
        type='recharge', 
        description__contains='新用户注册赠送'
    ).update(type='bonus')
    
    # 更新邀请返利
    updated2 = Bill.objects.filter(
        type='recharge', 
        description__contains='邀请返利'
    ).update(type='bonus')
    
    print(f'更新了 {updated1 + updated2} 条记录（新用户赠送: {updated1}, 邀请返利: {updated2}）')


class Migration(migrations.Migration):
    
    dependencies = [
        ('users', '0015_add_bonus_type_to_bill'),
    ]
    
    operations = [
        migrations.RunPython(update_bonus_bills, migrations.RunPython.noop),
    ]
