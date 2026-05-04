import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from apps.users.models import User
users = User.objects.all().values('id', 'username', 'email', 'role', 'balance')
for u in users:
    print(u)
