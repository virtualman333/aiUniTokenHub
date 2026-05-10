from rest_framework import serializers
from .models import User, APIKey, Bill, CardPassword, InviteConfig, InviteReward, RechargeChannel, RechargePackage


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
    email = serializers.EmailField(required=True, allow_blank=False)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    company = serializers.CharField(required=False, allow_blank=True, max_length=200)
    invite_code = serializers.CharField(required=False, allow_blank=True, max_length=16, write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'phone', 'company', 'invite_code']
        extra_kwargs = {
            'username': {'required': True},
        }
    
    def validate(self, attrs):
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({'password_confirm': '两次密码不一致'})
        # 唯一性校验
        username = attrs.get('username')
        email = attrs.get('email')
        if username and User.objects.filter(username=username).exists():
            raise serializers.ValidationError({'username': '用户名已被使用'})
        if email and User.objects.filter(email=email).exists():
            raise serializers.ValidationError({'email': '邮箱已被使用'})
        invite_code = attrs.pop('invite_code', '')
        if invite_code:
            try:
                inviter = User.objects.get(invite_code=invite_code)
                attrs['invited_by'] = inviter
            except User.DoesNotExist:
                raise serializers.ValidationError({'invite_code': '邀请码无效'})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm', None)
        password = validated_data.pop('password')
        from .utils import generate_invite_code
        validated_data['invite_code'] = generate_invite_code()
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


class BillSerializer(serializers.ModelSerializer):
    """账单记录"""
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    amount = serializers.FloatField()
    balance = serializers.FloatField()

    class Meta:
        model = Bill
        fields = ['id', 'type', 'type_display', 'amount', 'balance', 'description', 'created_at']
        read_only_fields = ['id', 'type', 'amount', 'balance', 'description', 'created_at']


class CardPasswordSerializer(serializers.ModelSerializer):
    """卡密序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    used_by_username = serializers.CharField(source='used_by.username', read_only=True, default=None)
    channel_name = serializers.CharField(source='channel.name', read_only=True, default=None)
    amount = serializers.FloatField()

    class Meta:
        model = CardPassword
        fields = ['id', 'code', 'amount', 'status', 'status_display', 'batch_no', 'channel', 'channel_name',
                  'used_by', 'used_by_username', 'used_at', 'remark', 'created_at']
        read_only_fields = ['id', 'code', 'status', 'used_by', 'used_at', 'created_at']


class CardRedeemSerializer(serializers.Serializer):
    """卡密兑换序列化器"""
    code = serializers.CharField(max_length=32, help_text='卡密码')


class InviteConfigSerializer(serializers.ModelSerializer):
    """邀请返利配置序列化器"""
    rebate_type_display = serializers.CharField(source='get_rebate_type_display', read_only=True)
    
    class Meta:
        model = InviteConfig
        fields = ['id', 'rebate_type', 'rebate_type_display', 'rebate_ratio', 'upgrade_threshold',
                  'reward_threshold', 'rebate_description', 'updated_at']
        read_only_fields = ['id', 'updated_at']


class InviteRewardSerializer(serializers.ModelSerializer):
    """邀请返利记录序列化器"""
    inviter_username = serializers.CharField(source='inviter.username', read_only=True)
    invitee_username = serializers.CharField(source='invitee.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    recharge_amount = serializers.FloatField()
    reward_amount = serializers.FloatField()
    
    class Meta:
        model = InviteReward
        fields = ['id', 'inviter', 'inviter_username', 'invitee', 'invitee_username',
                  'recharge_amount', 'reward_amount', 'status', 'status_display',
                  'reviewed_at', 'created_at']
        read_only_fields = ['id', 'inviter', 'invitee', 'recharge_amount', 'reward_amount',
                            'status', 'reviewed_at', 'created_at']


class InviteInfoSerializer(serializers.Serializer):
    """邀请信息汇总序列化器"""
    invite_code = serializers.CharField()
    invite_link = serializers.CharField()
    invite_count = serializers.IntegerField()
    total_reward = serializers.FloatField()
    config = InviteConfigSerializer()


class RechargeChannelSerializer(serializers.ModelSerializer):
    """充值渠道序列化器"""
    package_count = serializers.SerializerMethodField()
    
    class Meta:
        model = RechargeChannel
        fields = ['id', 'name', 'code', 'description', 'icon',
                  'is_active', 'sort_order', 'package_count', 'created_at']
    
    def get_package_count(self, obj):
        return obj.packages.filter(is_active=True).count()


class RechargePackageSerializer(serializers.ModelSerializer):
    """充值套餐序列化器"""
    channel_name = serializers.CharField(source='channel.name', read_only=True, default='')
    actual_amount = serializers.SerializerMethodField()
    redirect_url = serializers.CharField(allow_blank=True, required=False)
    callback_url = serializers.CharField(allow_blank=True, required=False)
    
    class Meta:
        model = RechargePackage
        fields = ['id', 'channel', 'channel_name', 'amount', 'bonus', 'actual_amount',
                  'redirect_url', 'callback_url', 'is_active', 'sort_order', 'description', 'created_at']
    
    def get_actual_amount(self, obj):
        """实际到账金额"""
        return float(obj.amount + obj.bonus)


class RechargeSerializer(serializers.Serializer):
    """充值请求序列化器"""
    channel_id = serializers.IntegerField(required=False, help_text='充值渠道ID')
    package_id = serializers.IntegerField(required=False, help_text='充值套餐ID')
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, 
                                     help_text='自定义金额（不使用套餐时）')
    payment_method = serializers.CharField(required=False, default='balance',
                                           help_text='支付方式：balance=余额')

