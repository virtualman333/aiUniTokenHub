"""
Init test users script
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.users.models import User
from apps.ai_models.models import ModelProvider, AIModel

def init_users():
    """Create test users"""
    
    # Create or update admin account
    admin, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@example.com',
            'balance': 10000.00,
            'company': 'uniTokenHub',
        }
    )
    admin.role = 'admin'
    admin.is_staff = True
    admin.is_superuser = True
    admin.is_active = True
    admin.set_password('admin123')
    admin.save()
    print(f'[OK] Admin account: admin / admin123 (role={admin.role})')
    
    # Create or update normal user account
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
            'balance': 1000.00,
            'company': 'Test Company',
        }
    )
    user.role = 'user'
    user.is_active = True
    user.set_password('test123')
    user.save()
    print(f'[OK] Test user account: testuser / test123 (role={user.role})')

def init_providers():
    """Init sample model providers"""
    
    providers = [
        {
            'name': 'OpenAI',
            'code': 'openai',
            'website': 'https://openai.com',
            'description': 'OpenAI - Leading AI research organization',
            'is_active': True,
        },
        {
            'name': 'Anthropic',
            'code': 'anthropic',
            'website': 'https://anthropic.com',
            'description': 'Anthropic - AI safety and research',
            'is_active': True,
        },
        {
            'name': 'Google',
            'code': 'google',
            'website': 'https://ai.google',
            'description': 'Google AI - Gemini models',
            'is_active': True,
        },
    ]
    
    for p_data in providers:
        p, created = ModelProvider.objects.get_or_create(
            code=p_data['code'],
            defaults=p_data
        )
        if created:
            print(f'[OK] Provider created: {p.name}')

if __name__ == '__main__':
    print('=' * 50)
    print('[Init] Starting data initialization...')
    print('=' * 50)
    
    print('\n[*] Initializing users...')
    init_users()
    
    print('\n[*] Initializing model providers...')
    init_providers()
    
    print('\n' + '=' * 50)
    print('[OK] Initialization complete!')
    print('=' * 50)
    print('\nTest Accounts:')
    print('  Admin: admin / admin123')
    print('  User:  testuser / test123')
