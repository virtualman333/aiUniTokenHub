import random
import string
from decimal import Decimal
from django.db import transaction
from .models import User, InviteConfig, InviteReward, Bill

# 常见的匿名/临时邮箱域名黑名单
DISPOSABLE_EMAIL_DOMAINS = {
    'duck.com',
    'tempmail.org',
    'tempmail.com',
    '10minutemail.com',
    '10minutemail.net',
    'guerrillamail.com',
    'guerrillamail.net',
    'guerrillamail.org',
    'mailinator.com',
    'mailinator.net',
    'mailinator.org',
    'yopmail.com',
    'yopmail.net',
    'yopmail.org',
    'temp-mail.org',
    'temp-mail.com',
    'disposablemail.com',
    'sharklasers.com',
    'grr.la',
    'guerrillamailblock.com',
    'pokemail.net',
    'spam4.me',
    'bccto.me',
    'chacuo.net',
    'facilelogin.com',
    'fexbox.org',
    'fidalgo.net',
    'filzmail.com',
    'fmetrics.org',
    'foofly.net',
    'bootq.com',
    'spamherelots.com',
    'thisisnotmyrealemail.com',
    'trash-mail.com',
    'trashmail.com',
    'trashmail.net',
    'dumpmail.de',
    'emailisvalid.com',
    'emz.net',
    'erenth.com',
    'europemail.com',
    'everymail.net',
    'example.com',
    'fakemail.net',
    'fakeinbox.com',
    'fastacura.com',
    'getairmail.com',
    'getnada.com',
    'givmail.com',
    'gotmail.net',
    'hidemail.de',
    'hmamail.com',
    'imails.info',
    'inboxalias.com',
    'inboxclean.com',
    'incognitomail.com',
    'jetable.org',
    'junkmail.com',
    'kasmail.com',
    'kulturbetrieb.info',
    'lifebyfood.com',
    'litedrop.com',
    'lookugly.com',
    'lopl.co',
    'lr78.com',
    'm4il.net',
    'mailcatch.com',
    'mailde.de',
    'maildrop.cc',
    'maileater.com',
    'mailexpire.com',
    'mailfreeonline.com',
    'mailin8r.com',
    'mailinater.com',
    'mailmetrash.com',
    'mailmoat.com',
    'mailnull.com',
    'mailpick.biz',
    'mailrockers.com',
    'mailshell.com',
    'mailsiphon.com',
    'mailtemp.com',
    'mailtothis.com',
    'mailzilla.com',
    'mbx.cc',
    'meltmail.com',
    'mintemail.com',
    'mycleaninbox.net',
    'myemailboxy.com',
    'mymail.in',
    'myspamless.com',
    'noclickemail.com',
    'nogmailspam.info',
    'nomail.xl.cx',
    'nospam.ze.tc',
    'notmailinator.com',
    'objectmail.com',
    'obobbo.com',
    'onewaymail.com',
    'ordinaryamerican.net',
    'owlpic.com',
    'pookmail.com',
    'proxymail.net',
    'quickinbox.com',
    'rcpt.at',
    'reallymymail.com',
    'recode.me',
    'recursor.net',
    'regbypass.com',
    'rejectmail.com',
    'rppkn.com',
    's0ny.net',
    'safe-mail.net',
    'safetymail.info',
    'sandelf.de',
    'saynotospams.com',
    'selfdestructingmail.com',
    'sendspamhere.com',
    'shieldedmail.com',
    'shiftmail.com',
    'shitmail.de',
    'shitmail.org',
    'shortmail.net',
    'sify.com',
    'skeefmail.com',
    'slopsbox.com',
    'smashmail.de',
    'snakemail.com',
    'sneakemail.com',
    'sofortmail.de',
    'sogetthis.com',
    'spam.la',
    'spam.su',
    'spamavert.com',
    'spambob.net',
    'spambog.com',
    'spambox.info',
    'spambox.us',
    'spamcero.com',
    'spamcannon.com',
    'spamcannon.net',
    'spamcontol.net',
    'spamcorpt.net',
    'spamcowboy.com',
    'spamcowboy.net',
    'spamcowboy.org',
    'spamday.com',
    'spamdecoy.net',
    'spamfree24.com',
    'spamfree24.de',
    'spamfree24.eu',
    'spamfree24.info',
    'spamfree24.net',
    'spamfree24.org',
    'spamgoes.in',
    'spamgourmet.com',
    'spamgourmet.net',
    'spamgourmet.org',
    'spaminator.de',
    'spaminator.com',
    'spamkill.info',
    'spaml.com',
    'spaml.de',
    'spammotel.com',
    'spamnotagain.com',
    'spamoclock.com',
    'spamproxy.net',
    'spamserver.net',
    'spamservice.com',
    'spamspot.com',
    'spamstack.net',
    'spamstore.net',
    'spamthrotector.com',
    'spamthrotector.net',
    'spamthrotector.org',
    'spamtrap.ro',
    'spamtraps.biz',
    'spamwall.net',
    'spamway.com',
    'spamwise.net',
    'speedeemail.com',
    'squizzy.de',
    'suremail.info',
    'teewars.org',
    'temporaryemail.net',
    'temporarioemail.com',
    'tempemail.biz',
    'tempemail.com',
    'tempemail.net',
    'tempinbox.com',
    'tempomail.fr',
    'temporarily.de',
    'thankyou2010.com',
    'thecloudindex.com',
    'thisisnotmyrealemail.com',
    'thismail.net',
    'throwawayemailaddress.com',
    'tilien.com',
    'tmail.com',
    'tmailinator.com',
    'tradermail.info',
    'trash-amil.com',
    'trash2009.com',
    'trashmail.justforwardit.com',
    'trashmailme.com',
    'trashymail.com',
    'trialmail.de',
    'tvstar.xyz',
    'tyldd.com',
    'uggsrock.com',
    'umail.net',
    'unmail.info',
    'upliftnow.com',
    'uplipht.com',
    'venompen.com',
    'veryrealemail.com',
    'viditag.com',
    'vipmail.pw',
    'vmsg.io',
    'vubby.com',
    'walala.org',
    'watchfull.net',
    'webm4il.info',
    'wh4f.org',
    'whyspam.me',
    'willhackforfood.biz',
    'willselfdestruct.com',
    'winemaven.info',
    'wronghead.com',
    'wuzup.net',
    'wuzupmail.net',
    'xagloo.com',
    'xemaps.com',
    'xmail.com',
    'yogamaven.com',
    'yopmail.fr',
    'yopweb.com',
    'yourdomain.com',
    'zehnminuten.de',
    'zehnminutenmail.de',
    'zetmail.com',
    'zippymail.info',
    'zoaxe.com',
    'zumpul.com',
}


def is_disposable_email(email):
    """
    检查邮箱是否为匿名/临时邮箱
    
    Args:
        email: 邮箱地址
    
    Returns:
        bool: 如果是匿名邮箱返回 True，否则返回 False
    """
    try:
        domain = email.split('@')[-1].lower()
        
        # 先从数据库配置中读取黑名单
        try:
            from .models import EmailConfig
            cfg = EmailConfig.get_config()
            if cfg.blocked_email_domains:
                # 按行分割，去除空行和前后空格
                blocked_domains = {
                    d.strip().lower() 
                    for d in cfg.blocked_email_domains.split('\n') 
                    if d.strip()
                }
                if domain in blocked_domains:
                    return True
        except Exception:
            pass  # 如果数据库读取失败，使用硬编码列表
        
        # 如果数据库中没有配置，使用硬编码的默认列表
        return domain in DISPOSABLE_EMAIL_DOMAINS
    except (IndexError, AttributeError):
        return False


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
                type='bonus',
                amount=reward_amount,
                balance=inviter.balance,
                description=f'邀请返利（来自{user.username}充值）'
            )