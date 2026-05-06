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
    EmailConfig, EmailVerifyCode,
)
from .serializers import (
    UserRegisterSerializer, UserLoginSerializer, UserSerializer,
    APIKeySerializer, ChangePasswordSerializer, BillSerializer,
    CardPasswordSerializer, CardRedeemSerializer,
    InviteConfigSerializer, InviteRewardSerializer
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

        # 标记验证码已使用
        record.is_used = True
        record.save(update_fields=['is_used'])

        token = generate_token(user)
        return APIResponse.created({
            'user': UserSerializer(user).data,
            'token': token
        }, '注册成功')
    
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
