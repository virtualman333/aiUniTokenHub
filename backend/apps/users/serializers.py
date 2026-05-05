from rest_framework import serializers
from .models import User, APIKey


class AdminUserSerializer(serializers.ModelSerializer):
    """管理员用户序列化器"""
    balance = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'phone', 'company', 
                  'balance', 'is_active', 'is_staff', 'is_superuser', 'created_at']
        read_only_fields = ['id', 'is_staff', 'is_superuser', 'created_at']
    
    def get_balance(self, obj):
        """确保balance返回浮点数而非Decimal"""
        return float(obj.balance) if obj.balance else 0.0


class UserRegisterSerializer(serializers.ModelSerializer):
    """用户注册"""
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    company = serializers.CharField(required=False, allow_blank=True, max_length=200)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'phone', 'company']
        extra_kwargs = {
            'username': {'required': True},
        }
    
    def validate(self, attrs):
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({'password_confirm': '两次密码不一致'})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm', None)
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserLoginSerializer(serializers.Serializer):
    """用户登录"""
    username = serializers.CharField()
    password = serializers.CharField()


class UserSerializer(serializers.ModelSerializer):
    """用户详情"""
    balance = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'phone', 'company', 'balance', 'created_at']
        read_only_fields = ['id', 'role', 'balance', 'created_at']
    
    def get_balance(self, obj):
        """确保balance返回浮点数而非Decimal"""
        return float(obj.balance) if obj.balance else 0.0


class APIKeySerializer(serializers.ModelSerializer):
    """API密钥"""
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = APIKey
        fields = ['id', 'key', 'name', 'is_active', 'expires_at', 'allow_ips', 
                  'rate_limit', 'is_expired', 'created_at']
        read_only_fields = ['id', 'key', 'created_at']
    
    def create(self, validated_data):
        from .authentication import generate_api_key
        validated_data['key'] = generate_api_key()
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ChangePasswordSerializer(serializers.Serializer):
    """修改密码"""
    old_password = serializers.CharField()
    new_password = serializers.CharField(min_length=6)
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('原密码错误')
        return value
