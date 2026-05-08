#!/usr/bin/env python
"""
创建初始用户脚本
运行方式: python scripts/create_initial_users.py
"""
import os
import sys
import django

# 设置 Django 环境
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.users.models import User
from apps.users.utils import generate_invite_code


def create_initial_users():
    """创建初始测试用户"""
    
    # 创建管理员用户
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@example.com',
            'role': 'admin',
            'is_active': True,
            'is_staff': True,
            'is_superuser': True,
            'invite_code': generate_invite_code(),
        }
    )
    
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        print("OK: 管理员用户创建成功: admin / admin123")
    else:
        print("INFO: 管理员用户已存在")
    
    # 创建测试普通用户
    test_user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'testuser@example.com',
            'role': 'user',
            'is_active': True,
            'invite_code': generate_invite_code(),
        }
    )
    
    if created:
        test_user.set_password('test123')
        test_user.save()
        print("OK: 测试用户创建成功: testuser / test123")
    else:
        print("INFO: 测试用户已存在")


if __name__ == '__main__':
    create_initial_users()
