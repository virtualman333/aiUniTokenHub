import random
import string
from decimal import Decimal
from django.db import transaction
from .models import User, InviteConfig, InviteReward, Bill


def generate_invite_code():
    """生成唯一的8位邀请码（大写字母+数字）"""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if not User.objects.filter(invite_code=code).exists():
            return code


def process_invite_reward(user, recharge_amount):
    """处理邀请返利逻辑
    
    Args:
        user: 充值用户
        recharge_amount: 充值金额
    """
    if not user.invited_by:
        return
    inviter = user.invited_by
    config = InviteConfig.get_config()
    rebate_type = config.rebate_type
    rebate_ratio = Decimal(str(config.rebate_ratio))
    reward_amount = Decimal(str(recharge_amount)) * rebate_ratio
    if reward_amount <= 0:
        return
    should_reward = False
    if rebate_type == 'first':
        if not InviteReward.objects.filter(inviter=inviter, invitee=user, status__in=['approved', 'pending']).exists():
            should_reward = True
    elif rebate_type == 'every':
        should_reward = True
    elif rebate_type == 'upgrade':
        approved_count = InviteReward.objects.filter(inviter=inviter, status='approved').values('invitee').distinct().count()
        if approved_count >= config.upgrade_threshold:
            should_reward = True
        elif not InviteReward.objects.filter(inviter=inviter, invitee=user, status__in=['approved', 'pending']).exists():
            should_reward = True
    if not should_reward:
        return
    reward_threshold = Decimal(str(config.reward_threshold))
    if reward_amount >= reward_threshold:
        InviteReward.objects.create(
            inviter=inviter,
            invitee=user,
            recharge_amount=recharge_amount,
            reward_amount=reward_amount,
            status='pending'
        )
    else:
        with transaction.atomic():
            InviteReward.objects.create(
                inviter=inviter,
                invitee=user,
                recharge_amount=recharge_amount,
                reward_amount=reward_amount,
                status='approved'
            )
            inviter.balance += reward_amount
            inviter.save()
            Bill.objects.create(
                user=inviter,
                type='recharge',
                amount=reward_amount,
                balance=inviter.balance,
                description=f'邀请返利（来自{user.username}充值）'
            )