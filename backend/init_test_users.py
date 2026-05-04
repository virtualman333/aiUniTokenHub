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
from apps.api_proxy.models import APICategory, APIEndpoint

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

def init_apis():
    """Init sample APIs"""
    
    categories = [
        {'name': 'LLM', 'icon': 'chat', 'order': 1},
        {'name': 'Vision', 'icon': 'picture', 'order': 2},
        {'name': 'Audio', 'icon': 'microphone', 'order': 3},
        {'name': 'Search', 'icon': 'search', 'order': 4},
    ]
    
    for cat_data in categories:
        cat, created = APICategory.objects.get_or_create(
            name=cat_data['name'],
            defaults=cat_data
        )
        if created:
            print(f'[OK] Category created: {cat.name}')
    
    endpoints = [
        {
            'category': APICategory.objects.get(name='LLM'),
            'name': 'ChatGPT-4o',
            'path': '/v1/chat/completions',
            'method': 'POST',
            'description': 'OpenAI latest multimodal LLM',
            'target_url': 'https://api.openai.com/v1/chat/completions',
            'is_public': False,
            'price': 0.01
        },
        {
            'category': APICategory.objects.get(name='LLM'),
            'name': 'Claude-3.5',
            'path': '/v1/messages',
            'method': 'POST',
            'description': 'Anthropic best reasoning model',
            'target_url': 'https://api.anthropic.com/v1/messages',
            'is_public': False,
            'price': 0.015
        },
        {
            'category': APICategory.objects.get(name='Vision'),
            'name': 'GPT-4V Image',
            'path': '/v1/chat/completions',
            'method': 'POST',
            'description': 'Multimodal API with image understanding',
            'target_url': 'https://api.openai.com/v1/chat/completions',
            'is_public': False,
            'price': 0.0125
        },
        {
            'category': APICategory.objects.get(name='Search'),
            'name': 'SerpAPI Search',
            'path': '/search',
            'method': 'GET',
            'description': 'Google search results API',
            'target_url': 'https://serpapi.com/search',
            'is_public': False,
            'price': 0.005
        },
    ]
    
    for ep_data in endpoints:
        ep, created = APIEndpoint.objects.get_or_create(
            path=ep_data['path'],
            method=ep_data['method'],
            category=ep_data['category'],
            defaults=ep_data
        )
        if created:
            print(f'[OK] API created: {ep.name}')

if __name__ == '__main__':
    print('=' * 50)
    print('[Init] Starting data initialization...')
    print('=' * 50)
    
    print('\n[*] Initializing users...')
    init_users()
    
    print('\n[*] Initializing sample APIs...')
    init_apis()
    
    print('\n' + '=' * 50)
    print('[OK] Initialization complete!')
    print('=' * 50)
    print('\nTest Accounts:')
    print('  Admin: admin / admin123')
    print('  User:  testuser / test123')
