from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    """自定义用户模型"""
    
    ROLE_CHOICES = [
        ('admin', '管理员'),
        ('user', '普通用户'),
    ]
    
    role = models.CharField('角色', max_length=20, choices=ROLE_CHOICES, default='user')
    phone = models.CharField('手机号', max_length=20, blank=True, null=True)
    company = models.CharField('公司名称', max_length=200, blank=True, null=True)
    balance = models.DecimalField('余额', max_digits=12, decimal_places=4, default=0)
    invite_code = models.CharField('邀请码', max_length=16, unique=True, blank=True, null=True, db_index=True)
    invited_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='invitees', verbose_name='邀请人')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'users'
        verbose_name = '用户'
        verbose_name_plural = '用户'

    def __str__(self):
        return self.username


class APIKey(models.Model):
    """API密钥"""
    
    key = models.CharField('密钥', max_length=64, unique=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys')
    name = models.CharField('密钥名称', max_length=100)
    is_active = models.BooleanField('是否启用', default=True)
    expires_at = models.DateTimeField('过期时间', blank=True, null=True)
    allow_ips = models.TextField('允许访问IP', blank=True, help_text='多个IP用逗号分隔，留空表示不限制')
    rate_limit = models.IntegerField('速率限制(次/分钟)', default=60)
    
    # 额度控制
    remaining_calls = models.IntegerField('剩余调用次数', null=True, blank=True,
                                         help_text='null表示无限制')
    total_calls = models.IntegerField('总调用次数', default=0)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'api_keys'
        verbose_name = 'API密钥'
        verbose_name_plural = 'API密钥'

    def __str__(self):
        return f"{self.name} ({self.user.username})"
    
    @property
    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False


class UsageLog(models.Model):
    """使用日志"""
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='usage_logs')
    api_key = models.ForeignKey(APIKey, on_delete=models.SET_NULL, null=True, related_name='usage_logs')
    method = models.CharField('请求方法', max_length=10)
    endpoint = models.CharField('请求路径', max_length=500)
    request_headers = models.TextField('请求头', blank=True)
    request_body = models.TextField('请求体', blank=True)
    response_body = models.TextField('响应体', blank=True)
    status_code = models.IntegerField('状态码', default=0)
    response_time = models.IntegerField('响应时间(ms)', default=0)
    
    # Token 使用统计
    input_tokens = models.IntegerField('输入Token', default=0)
    output_tokens = models.IntegerField('输出Token', default=0)
    total_tokens = models.IntegerField('总Token', default=0)
    cached_tokens = models.IntegerField('缓存命中Token', default=0)
    cost = models.DecimalField('费用(元)', max_digits=12, decimal_places=6, default=0)
    
    ip_address = models.GenericIPAddressField('IP地址', null=True, blank=True)
    error_message = models.TextField('错误信息', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'usage_logs'
        verbose_name = '使用日志'
        verbose_name_plural = '使用日志'
        ordering = ('-created_at',)


class Bill(models.Model):
    """账单/交易记录"""

    TYPE_CHOICES = [
        ('recharge', '充值'),
        ('consume', '消费'),
        ('refund', '退款'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bills')
    type = models.CharField('交易类型', max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField('交易金额', max_digits=12, decimal_places=4)
    balance = models.DecimalField('交易后余额', max_digits=12, decimal_places=4)
    description = models.CharField('交易说明', max_length=500, blank=True)
    usage_log = models.ForeignKey(
        'UsageLog', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='bills', verbose_name='关联使用日志'
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'bills'
        verbose_name = '账单'
        verbose_name_plural = '账单'
        ordering = ('-created_at',)

    def __str__(self):
        return f"{self.get_type_display()} ¥{self.amount} ({self.user.username})"


class CardPassword(models.Model):
    """卡密"""

    STATUS_CHOICES = [
        ('unused', '未使用'),
        ('used', '已使用'),
    ]

    code = models.CharField('卡密', max_length=32, unique=True, db_index=True)
    amount = models.DecimalField('面值', max_digits=10, decimal_places=2)
    status = models.CharField('状态', max_length=10, choices=STATUS_CHOICES, default='unused')
    batch_no = models.CharField('批次号', max_length=50, blank=True, help_text='批量生成时的批次标识')
    used_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='used_cards', verbose_name='使用者'
    )
    used_at = models.DateTimeField('使用时间', null=True, blank=True)
    remark = models.CharField('备注', max_length=200, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'card_passwords'
        verbose_name = '卡密'
        verbose_name_plural = '卡密'
        ordering = ('-created_at',)

    def __str__(self):
        return f"{self.code} ¥{self.amount} ({self.get_status_display()})"


class InviteConfig(models.Model):
    """邀请返利配置（单例）"""
    
    REBATE_TYPE_CHOICES = [
        ('first', '首次返利'),
        ('every', '每次返利'),
        ('upgrade', '满X人升级为每次返利'),
    ]
    
    rebate_type = models.CharField('返利方式', max_length=20, choices=REBATE_TYPE_CHOICES, default='first')
    rebate_ratio = models.DecimalField('返利比例', max_digits=5, decimal_places=4, default=0.10, help_text='如0.10表示10%')
    upgrade_threshold = models.IntegerField('升级所需邀请人数', default=10, help_text='仅upgrade类型有效')
    reward_threshold = models.DecimalField('返利审核阈值', max_digits=10, decimal_places=2, default=100, help_text='单笔返利金额达到此值需审核')
    rebate_description = models.TextField('返利说明', blank=True, default='邀请好友注册并充值，您可获得返利奖励。')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'invite_config'
        verbose_name = '邀请返利配置'
        verbose_name_plural = '邀请返利配置'
    
    def __str__(self):
        return f"返利配置({self.get_rebate_type_display()})"
    
    @classmethod
    def get_config(cls):
        """获取或创建默认配置"""
        config, _ = cls.objects.get_or_create(pk=1)
        return config


class InviteReward(models.Model):
    """邀请返利记录"""
    
    STATUS_CHOICES = [
        ('pending', '待审核'),
        ('approved', '已通过'),
        ('rejected', '已拒绝'),
    ]
    
    inviter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invite_rewards', verbose_name='邀请人')
    invitee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invite_reward_records', verbose_name='被邀请人')
    recharge_amount = models.DecimalField('充值金额', max_digits=10, decimal_places=2)
    reward_amount = models.DecimalField('返利金额', max_digits=10, decimal_places=2)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_at = models.DateTimeField('审核时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        db_table = 'invite_rewards'
        verbose_name = '邀请返利记录'
        verbose_name_plural = '邀请返利记录'
        ordering = ('-created_at',)
    
    def __str__(self):
        return f"{self.inviter.username} <- {self.invitee.username} ¥{self.reward_amount}"


class EmailConfig(models.Model):
    """邮箱发送配置（单例）。后台可视化配置 SMTP。"""

    is_enabled = models.BooleanField('启用邮箱服务', default=False)
    smtp_host = models.CharField('SMTP 服务器', max_length=200, blank=True, default='')
    smtp_port = models.IntegerField('SMTP 端口', default=465)
    use_ssl = models.BooleanField('使用 SSL', default=True,
                                  help_text='465 端口建议 SSL；587 端口建议 TLS（关闭 SSL）')
    use_tls = models.BooleanField('使用 TLS (STARTTLS)', default=False)
    smtp_user = models.CharField('SMTP 用户名', max_length=200, blank=True, default='')
    smtp_password = models.CharField('SMTP 密码/授权码', max_length=255, blank=True, default='')
    from_email = models.CharField('发件人邮箱', max_length=200, blank=True, default='',
                                  help_text='可与 smtp_user 不同；通常填同一个邮箱地址')
    from_name = models.CharField('发件人名称', max_length=200, blank=True, default='uniTokenHub')

    code_expire_minutes = models.IntegerField('验证码有效期（分钟）', default=5)
    code_resend_seconds = models.IntegerField('验证码重发间隔（秒）', default=60)
    daily_limit_per_email = models.IntegerField('单邮箱每日发送上限', default=10)

    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'email_config'
        verbose_name = '邮箱配置'
        verbose_name_plural = '邮箱配置'

    def __str__(self):
        return f'EmailConfig(enabled={self.is_enabled})'

    @classmethod
    def get_config(cls):
        cfg, _ = cls.objects.get_or_create(pk=1)
        return cfg


class EmailVerifyCode(models.Model):
    """邮箱验证码记录"""

    PURPOSE_CHOICES = [
        ('register', '注册'),
        ('reset_password', '重置密码'),
    ]

    email = models.EmailField('邮箱', db_index=True)
    code = models.CharField('验证码', max_length=10)
    purpose = models.CharField('用途', max_length=32, choices=PURPOSE_CHOICES, default='register')
    is_used = models.BooleanField('已使用', default=False)
    expires_at = models.DateTimeField('过期时间')
    created_at = models.DateTimeField('创建时间', auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'email_verify_codes'
        verbose_name = '邮箱验证码'
        verbose_name_plural = '邮箱验证码'
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.email} {self.code} ({self.purpose})'

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return (not self.is_used) and (not self.is_expired)
