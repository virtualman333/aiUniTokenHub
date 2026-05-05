import jwt
import redis
from datetime import datetime, timedelta
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import User


class JWTAuthentication(BaseAuthentication):
    """JWT认证"""
    
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None
        
        try:
            prefix, token = auth_header.split(' ')
            if prefix.lower() != 'bearer':
                return None
        except ValueError:
            return None
        
        # 如果是 API Key（sk- 开头），不进行 JWT 验证，返回 None 让后续处理
        if token.startswith('sk-') or token.startswith('utk_'):
            return None
        
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token已过期')
        except jwt.InvalidTokenError:
            # 对于无效的 JWT token，返回 None 而不是抛异常
            # 这样 AllowAny 视图可以继续处理
            return None
        
        try:
            user = User.objects.get(id=payload['user_id'])
        except User.DoesNotExist:
            raise AuthenticationFailed('用户不存在')
        
        if not user.is_active:
            raise AuthenticationFailed('用户已被禁用')
        
        return (user, token)


def generate_token(user):
    """生成JWT Token"""
    expiration = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    payload = {
        'user_id': user.id,
        'username': user.username,
        'role': user.role,
        'exp': expiration,
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token


def generate_api_key():
    """生成标准 OpenAI 格式的 API Key"""
    import secrets
    return f"sk-{secrets.token_urlsafe(32)}"
