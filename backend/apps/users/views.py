import secrets
import random
from datetime import timedelta
from decimal import Decimal

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from django.contrib.auth import authenticate
from django.db import models as db_models
from django.utils import timezone
from .models import (
    User, APIKey, Bill, CardPassword, InviteConfig, InviteReward,
    EmailConfig, EmailVerifyCode, RechargeChannel, RechargePackage,
)
from .serializers import (
    UserRegisterSerializer, UserLoginSerializer, UserSerializer,
    APIKeySerializer, ChangePasswordSerializer, BillSerializer,
    CardPasswordSerializer, CardRedeemSerializer,
    InviteConfigSerializer, InviteRewardSerializer,
    RechargeChannelSerializer, RechargePackageSerializer, RechargeSerializer
)
from .authentication import generate_token
from .mailer import send_email, render_verify_code_email, EmailNotConfigured
from apps.utils.response import APIResponse


class AuthViewSet(viewsets.GenericViewSet):
    """认证视图集"""
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'], url_path='send_email_code')
    def send_email_code(self, request):
        """发送邮箱验证码（注册用）"""
        email = (request.data.get('email') or '').strip().lower()
        purpose = request.data.get('purpose') or 'register'

        if not email:
            return APIResponse.error('邮箱不能为空', 400)
        if '@' not in email or '.' not in email:
            return APIResponse.error('邮箱格式不正确', 400)

        cfg = EmailConfig.get_config()
        if not cfg.is_enabled:
            return APIResponse.error('邮箱服务未启用，请联系管理员', 503)

        # 注册场景：邮箱不能已被使用
        if purpose == 'register' and User.objects.filter(email=email).exists():
            return APIResponse.error('该邮箱已被注册', 400)

        now = timezone.now()

        # 频控：重发间隔
        last = (
            EmailVerifyCode.objects
            .filter(email=email, purpose=purpose)
            .order_by('-created_at')
            .first()
        )
        resend_seconds = max(10, int(cfg.code_resend_seconds or 60))
        if last and (now - last.created_at).total_seconds() < resend_seconds:
            wait = int(resend_seconds - (now - last.created_at).total_seconds())
            return APIResponse.error(f'请 {wait} 秒后再试', 429)

        # 频控：当日上限
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        sent_today = EmailVerifyCode.objects.filter(
            email=email, purpose=purpose, created_at__gte=today_start
        ).count()
        daily_limit = max(1, int(cfg.daily_limit_per_email or 10))
        if sent_today >= daily_limit:
            return APIResponse.error(f'当日发送已达上限（{daily_limit} 次），请明天再试', 429)

        # 生成 6 位数字验证码
        code = f'{random.randint(0, 999999):06d}'
        expire_minutes = max(1, int(cfg.code_expire_minutes or 5))
        record = EmailVerifyCode.objects.create(
            email=email,
            code=code,
            purpose=purpose,
            expires_at=now + timedelta(minutes=expire_minutes),
        )

        # 发送邮件
        try:
            subject, html, text = render_verify_code_email(code, expire_minutes, purpose)
            send_email(email, subject, html, text)
        except EmailNotConfigured as e:
            record.delete()
            return APIResponse.error(str(e), 503)
        except Exception as e:
            record.delete()
            return APIResponse.error(f'邮件发送失败：{e}', 500)

        return APIResponse.success({
            'expire_minutes': expire_minutes,
            'resend_seconds': resend_seconds,
        }, '验证码已发送，请查收邮件')

    @action(detail=False, methods=['post'])
    def register(self, request):
        """用户注册（需邮箱验证码）"""
        email = (request.data.get('email') or '').strip().lower()
        code = (request.data.get('email_code') or '').strip()

        if not email:
            return APIResponse.error('邮箱不能为空', 400)
        if not code:
            return APIResponse.error('请填写邮箱验证码', 400)

        # 校验验证码
        record = (
            EmailVerifyCode.objects
            .filter(email=email, purpose='register', is_used=False)
            .order_by('-created_at')
            .first()
        )
        if not record:
            return APIResponse.error('请先获取邮箱验证码', 400)
        if record.is_expired:
            return APIResponse.error('验证码已过期，请重新获取', 400)
        if record.code != code:
            return APIResponse.error('验证码不正确', 400)

        # 序列化注册（注意把 email 标准化）
        data = {**request.data, 'email': email}
        serializer = UserRegisterSerializer(data=data)
        if not serializer.is_valid():
            errors = serializer.errors
            first_error = list(errors.values())[0][0] if errors else '参数错误'
            return APIResponse.error(str(first_error), 400)
        user = serializer.save()

        # 新用户注册赠送1元
        welcome_amount = Decimal('1.00')
        user.balance = (user.balance or Decimal('0')) + welcome_amount
        user.save(update_fields=['balance'])
        Bill.objects.create(
            user=user,
            type='recharge',
            amount=welcome_amount,
            balance=user.balance,
            description='新用户注册赠送'
        )

        # 标记验证码已使用
        record.is_used = True
        record.save(update_fields=['is_used'])

        token = generate_token(user)
        return APIResponse.created({
            'user': UserSerializer(user).data,
            'token': token
        }, '注册成功，已赠送1元新人大礼包')
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        """用户登录"""
        serializer = UserLoginSerializer(data=request.data)
        if not serializer.is_valid():
            errors = serializer.errors
            first_error = list(errors.values())[0][0] if errors else '参数错误'
            return APIResponse.error(str(first_error), 400)
        
        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password']
        )
        
        if not user:
            return APIResponse.error('用户名或密码错误', 401)
        
        if not user.is_active:
            return APIResponse.error('账号已被禁用', 401)
        
        token = generate_token(user)
        return APIResponse.success({
            'user': UserSerializer(user).data,
            'token': token
        }, '登录成功')
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """获取当前用户信息"""
        return APIResponse.success(UserSerializer(request.user).data, '获取成功')
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """修改密码"""
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            errors = serializer.errors
            first_error = list(errors.values())[0][0] if errors else '参数错误'
            return APIResponse.error(str(first_error), 400)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return APIResponse.success(None, '密码修改成功')


class APIKeyViewSet(viewsets.ModelViewSet):
    """API密钥管理"""
    serializer_class = APIKeySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return APIKey.objects.filter(user=self.request.user)
    
    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return APIResponse.success(serializer.data, '获取成功')
    
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            errors = serializer.errors
            first_error = list(errors.values())[0][0] if errors else '参数错误'
            return APIResponse.error(str(first_error), 400)
        self.perform_create(serializer)
        return APIResponse.created(serializer.data, '创建成功')
    
    def destroy(self, request, pk=None):
        instance = self.get_object()
        instance.delete()
        return APIResponse.success(None, '删除成功')
    
    @action(detail=False, methods=['delete'])
    def revoke(self, request):
        """撤销密钥"""
        key_id = request.data.get('key_id')
        try:
            api_key = self.get_queryset().get(id=key_id)
            api_key.delete()
            return APIResponse.success(None, '密钥已撤销')
        except APIKey.DoesNotExist:
            return APIResponse.error('密钥不存在', 404)


class BillingViewSet(viewsets.GenericViewSet):
    """账单中心"""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def bills(self, request):
        """获取账单列表"""
        queryset = Bill.objects.filter(user=request.user)
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        bills = queryset[start:end]
        serializer = BillSerializer(bills, many=True)
        return APIResponse.paginated(serializer.data, total, page, page_size)

    @action(detail=False, methods=['get'], url_path='admin-bills')
    def admin_bills(self, request):
        """管理员查看所有用户账单"""
        # 检查管理员权限
        if not request.user or not request.user.is_staff:
            return APIResponse.error('无权限访问', 403)
        
        queryset = Bill.objects.all().select_related('user')

        # 过滤条件
        user_id = request.query_params.get('user')
        bill_type = request.query_params.get('type')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if bill_type:
            queryset = queryset.filter(type=bill_type)
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)

        # 分页
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        bills = queryset[start:end]

        serializer = BillSerializer(bills, many=True)
        return APIResponse.paginated(serializer.data, total, page, page_size)

    @action(detail=False, methods=['post'])
    def recharge(self, request):
        """账户充值（直接充值，无需支付网关）"""
        amount = request.data.get('amount')
        if not amount:
            return APIResponse.error('充值金额不能为空', 400)
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return APIResponse.error('无效的充值金额', 400)
        if amount <= 0:
            return APIResponse.error('充值金额必须大于0', 400)
        if amount > 10000:
            return APIResponse.error('单次充值金额不能超过10000元', 400)
        user = request.user
        user.balance += Decimal(str(amount))
        user.save()
        bill = Bill.objects.create(
            user=user,
            type='recharge',
            amount=amount,
            balance=user.balance,
            description=f'账户充值 ¥{amount:.2f}'
        )
        from .utils import process_invite_reward
        process_invite_reward(user, amount)
        return APIResponse.success({
            'bill': BillSerializer(bill).data,
            'balance': float(user.balance)
        }, '充值成功')

    @action(detail=False, methods=['post'], url_path='redeem')
    def redeem_card(self, request):
        """卡密兑换"""
        serializer = CardRedeemSerializer(data=request.data)
        if not serializer.is_valid():
            errors = serializer.errors
            first_error = list(errors.values())[0][0] if errors else '参数错误'
            return APIResponse.error(str(first_error), 400)
        code = serializer.validated_data['code'].strip()
        try:
            card = CardPassword.objects.get(code=code)
        except CardPassword.DoesNotExist:
            return APIResponse.error('卡密不存在', 404)
        if card.status == 'used':
            return APIResponse.error('该卡密已被使用', 400)
        user = request.user
        user.balance += card.amount
        user.save()
        card.status = 'used'
        card.used_by = user
        card.used_at = timezone.now()
        card.save()
        bill = Bill.objects.create(
            user=user,
            type='recharge',
            amount=card.amount,
            balance=user.balance,
            description=f'卡密充值 {code}'
        )
        from .utils import process_invite_reward
        process_invite_reward(user, card.amount)
        return APIResponse.success({
            'bill': BillSerializer(bill).data,
            'balance': float(user.balance),
            'card_amount': float(card.amount)
        }, f'卡密兑换成功，充值 ¥{card.amount:.2f}')


class CardPasswordViewSet(viewsets.GenericViewSet):
    """卡密管理（管理员）"""
    permission_classes = [IsAdminUser]

    @action(detail=False, methods=['get'])
    def list_cards(self, request):
        """获取卡密列表"""
        queryset = CardPassword.objects.all()
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        batch_no = request.query_params.get('batch_no')
        if batch_no:
            queryset = queryset.filter(batch_no=batch_no)
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        cards = queryset[start:end]
        serializer = CardPasswordSerializer(cards, many=True)
        return APIResponse.paginated(serializer.data, total, page, page_size)

    @action(detail=False, methods=['post'], url_path='generate')
    def generate_cards(self, request):
        """批量生成卡密"""
        amount = request.data.get('amount')
        count = request.data.get('count', 1)
        batch_no = request.data.get('batch_no', '')
        remark = request.data.get('remark', '')
        if not amount:
            return APIResponse.error('面值不能为空', 400)
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return APIResponse.error('无效的面值', 400)
        if amount <= 0:
            return APIResponse.error('面值必须大于0', 400)
        try:
            count = int(count)
        except (TypeError, ValueError):
            return APIResponse.error('无效的数量', 400)
        if count <= 0 or count > 1000:
            return APIResponse.error('数量必须在1-1000之间', 400)
        if not batch_no:
            batch_no = f"B{timezone.now().strftime('%Y%m%d%H%M%S')}"
        cards = []
        for _ in range(count):
            code = secrets.token_hex(16).upper()
            card = CardPassword.objects.create(
                code=code,
                amount=amount,
                batch_no=batch_no,
                remark=remark
            )
            cards.append(card)
        serializer = CardPasswordSerializer(cards, many=True)
        return APIResponse.success({
            'cards': serializer.data,
            'batch_no': batch_no,
            'count': count
        }, f'成功生成 {count} 张卡密')

    @action(detail=False, methods=['delete'], url_path='delete')
    def delete_cards(self, request):
        """删除卡密"""
        ids = request.data.get('ids', [])
        if not ids:
            return APIResponse.error('请选择要删除的卡密', 400)
        deleted, _ = CardPassword.objects.filter(id__in=ids, status='unused').delete()
        return APIResponse.success({'deleted': deleted}, f'成功删除 {deleted} 张卡密')


class InviteViewSet(viewsets.GenericViewSet):
    """邀请信息"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'], url_path='info')
    def invite_info(self, request):
        """获取邀请汇总信息"""
        user = request.user
        if not user.invite_code:
            from .utils import generate_invite_code
            user.invite_code = generate_invite_code()
            user.save()
        invite_count = User.objects.filter(invited_by=user).count()
        total_reward = InviteReward.objects.filter(
            inviter=user, status='approved'
        ).aggregate(total=db_models.Sum('reward_amount'))['total'] or 0
        config = InviteConfig.get_config()
        return APIResponse.success({
            'invite_code': user.invite_code,
            'invite_count': invite_count,
            'total_reward': float(total_reward),
            'config': InviteConfigSerializer(config).data
        }, '获取成功')
    
    @action(detail=False, methods=['get'], url_path='rewards')
    def invite_rewards(self, request):
        """获取收益记录（近10条）"""
        rewards = InviteReward.objects.filter(inviter=request.user)[:10]
        serializer = InviteRewardSerializer(rewards, many=True)
        return APIResponse.success(serializer.data, '获取成功')


class RechargeViewSet(viewsets.GenericViewSet):
    """充值管理"""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def channels(self, request):
        """获取所有启用的充值渠道"""
        channels = RechargeChannel.objects.filter(is_active=True)
        serializer = RechargeChannelSerializer(channels, many=True)
        return APIResponse.success(serializer.data, '获取成功')

    @action(detail=False, methods=['get'])
    def packages(self, request):
        """获取充值套餐列表"""
        channel_id = request.query_params.get('channel_id')
        packages = RechargePackage.objects.filter(is_active=True)
        if channel_id:
            packages = packages.filter(channel_id=channel_id)
        serializer = RechargePackageSerializer(packages, many=True)
        return APIResponse.success(serializer.data, '获取成功')

    @action(detail=False, methods=['post'])
    def submit(self, request):
        """提交充值请求 - 生成第三方网站跳转URL"""
        serializer = RechargeSerializer(data=request.data)
        if not serializer.is_valid():
            errors = serializer.errors
            first_error = list(errors.values())[0][0] if errors else '参数错误'
            return APIResponse.error(str(first_error), 400)
        
        user = request.user
        channel_id = serializer.validated_data.get('channel_id')
        package_id = serializer.validated_data.get('package_id')
        
        # 获取充值套餐
        if not package_id:
            return APIResponse.error('请选择充值套餐', 400)
        
        try:
            package = RechargePackage.objects.select_related('channel').get(
                id=package_id, channel_id=channel_id, is_active=True
            )
        except RechargePackage.DoesNotExist:
            return APIResponse.error('充值套餐不存在或已禁用', 404)
        
        channel = package.channel
        
        # 检查套餐是否配置了跳转URL
        if not package.redirect_url:
            return APIResponse.error('该套餐暂不支持在线充值，请联系管理员', 400)
        
        # 计算充值金额
        amount = package.amount
        bonus = package.bonus
        
        # 生成订单ID
        order_id = f"R{user.id}{timezone.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"
        
        # 构建跳转URL（替换占位符）
        redirect_url = package.redirect_url.format(
            amount=float(amount),
            bonus=float(bonus),
            total=float(amount + bonus),
            order_id=order_id,
            user_id=user.id,
            channel_id=channel.id,
            package_id=package_id
        )
        
        return APIResponse.success({
            'order_id': order_id,
            'redirect_url': redirect_url,
            'amount': float(amount),
            'bonus': float(bonus),
            'total': float(amount + bonus),
            'channel_name': channel.name,
            'package_name': f'¥{package.amount}' + (f'+赠¥{bonus}' if bonus > 0 else ''),
            'hint': '即将跳转到第三方支付页面，请在完成支付后获取卡密进行充值'
        }, '即将跳转到第三方充值页面')


class AdminRechargeViewSet(viewsets.GenericViewSet):
    """管理员充值渠道管理"""
    permission_classes = [IsAdminUser]

    @action(detail=False, methods=['get'])
    def list_channels(self, request):
        """获取充值渠道列表"""
        channels = RechargeChannel.objects.all()
        serializer = RechargeChannelSerializer(channels, many=True)
        return APIResponse.success(serializer.data, '获取成功')

    @action(detail=False, methods=['post'])
    def create_channel(self, request):
        """创建充值渠道"""
        name = request.data.get('name')
        code = request.data.get('code')
        if not name or not code:
            return APIResponse.error('名称和代码不能为空', 400)
        
        if RechargeChannel.objects.filter(code=code).exists():
            return APIResponse.error('渠道代码已存在', 400)
        
        channel = RechargeChannel.objects.create(
            name=name,
            code=code,
            description=request.data.get('description', ''),
            icon=request.data.get('icon', ''),
            is_active=request.data.get('is_active', True),
            sort_order=request.data.get('sort_order', 0)
        )
        return APIResponse.created(RechargeChannelSerializer(channel).data, '创建成功')

    @action(detail=False, methods=['put'], url_path='update_channel/(?P<pk>[^/.]+)')
    def update_channel(self, request, pk=None):
        """更新充值渠道"""
        try:
            channel = RechargeChannel.objects.get(pk=pk)
        except RechargeChannel.DoesNotExist:
            return APIResponse.error('渠道不存在', 404)
        
        if 'name' in request.data:
            channel.name = request.data['name']
        if 'description' in request.data:
            channel.description = request.data['description']
        if 'icon' in request.data:
            channel.icon = request.data['icon']
        if 'is_active' in request.data:
            channel.is_active = request.data['is_active']
        if 'sort_order' in request.data:
            channel.sort_order = request.data['sort_order']
        
        channel.save()
        return APIResponse.success(RechargeChannelSerializer(channel).data, '更新成功')

    @action(detail=False, methods=['delete'], url_path='delete_channel/(?P<pk>[^/.]+)')
    def delete_channel(self, request, pk=None):
        """删除充值渠道"""
        try:
            channel = RechargeChannel.objects.get(pk=pk)
        except RechargeChannel.DoesNotExist:
            return APIResponse.error('渠道不存在', 404)
        
        # 检查是否有套餐
        if channel.packages.exists():
            return APIResponse.error('请先删除该渠道下的所有套餐', 400)
        
        channel.delete()
        return APIResponse.success(None, '删除成功')

    @action(detail=False, methods=['get'])
    def list_packages(self, request):
        """获取充值套餐列表"""
        try:
            channel_id = request.query_params.get('channel_id')
            packages = RechargePackage.objects.select_related('channel').all()
            if channel_id:
                packages = packages.filter(channel_id=channel_id)
            serializer = RechargePackageSerializer(packages, many=True)
            return APIResponse.success(serializer.data, '获取成功')
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'list_packages error: {str(e)}', exc_info=True)
            return APIResponse.error('获取套餐列表失败', 500)

    @action(detail=False, methods=['post'])
    def create_package(self, request):
        """创建充值套餐"""
        channel_id = request.data.get('channel_id')
        amount = request.data.get('amount')
        redirect_url = request.data.get('redirect_url', '')
        
        if not channel_id:
            return APIResponse.error('请选择所属渠道', 400)
        if not amount:
            return APIResponse.error('金额不能为空', 400)
        if not redirect_url:
            return APIResponse.error('跳转URL不能为空', 400)
        
        try:
            channel = RechargeChannel.objects.get(id=channel_id)
        except RechargeChannel.DoesNotExist:
            return APIResponse.error('充值渠道不存在', 404)
        
        try:
            amount = Decimal(str(amount))
            if amount <= 0:
                return APIResponse.error('金额必须大于0', 400)
        except:
            return APIResponse.error('无效的金额', 400)
        
        package = RechargePackage.objects.create(
            channel=channel,
            amount=amount,
            bonus=Decimal(str(request.data.get('bonus', '0'))),
            redirect_url=redirect_url,
            callback_url=request.data.get('callback_url', ''),
            is_active=request.data.get('is_active', True),
            sort_order=request.data.get('sort_order', 0),
            description=request.data.get('description', '')
        )
        return APIResponse.created(RechargePackageSerializer(package).data, '创建成功')

    @action(detail=False, methods=['put'], url_path='update_package/(?P<pk>[^/.]+)')
    def update_package(self, request, pk=None):
        """更新充值套餐"""
        try:
            package = RechargePackage.objects.get(pk=pk)
        except RechargePackage.DoesNotExist:
            return APIResponse.error('套餐不存在', 404)
        
        if 'amount' in request.data:
            try:
                amount = Decimal(str(request.data['amount']))
                if amount <= 0:
                    return APIResponse.error('金额必须大于0', 400)
                package.amount = amount
            except:
                return APIResponse.error('无效的金额', 400)
        
        if 'bonus' in request.data:
            package.bonus = Decimal(str(request.data['bonus']))
        if 'redirect_url' in request.data:
            package.redirect_url = request.data['redirect_url']
        if 'callback_url' in request.data:
            package.callback_url = request.data['callback_url']
        if 'is_active' in request.data:
            package.is_active = request.data['is_active']
        if 'sort_order' in request.data:
            package.sort_order = request.data['sort_order']
        if 'description' in request.data:
            package.description = request.data['description']
        
        package.save()
        return APIResponse.success(RechargePackageSerializer(package).data, '更新成功')

    @action(detail=False, methods=['delete'], url_path='delete_package/(?P<pk>[^/.]+)')
    def delete_package(self, request, pk=None):
        """删除充值套餐"""
        try:
            package = RechargePackage.objects.get(pk=pk)
        except RechargePackage.DoesNotExist:
            return APIResponse.error('套餐不存在', 404)
        
        package.delete()
        return APIResponse.success(None, '删除成功')


