import random
import string
from django.db import transaction
from .models import User, InviteConfig, InviteReward, Bill
from .invite_reward import APPROVED, COUNTED_STATUSES, decide_reward

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
    """处理邀请返利逻辑 —— **判定在 `apps/users/invite_reward.py`，这里只负责落库**

    两件事从原来的写法里改掉了（都是钱的事）：

    1. **判定不再有第二份。** 原来这里自己写了一遍「哪种返利方式 × 有没有记录 ×
       满没满人」，与 `invite_reward.decide_reward` 是同一件事的两个副本 ——
       副本必然漂移（发多少、要不要审核都得说两遍）。现在这里只有一个调用点。
    2. **查询与写入在同一把锁里。** 原来 `filter(...).exists()` 在事务外、
       `inviter.balance += ...` 在事务内，中间那个窗口足够两次充值都判成「首次」，
       于是同一对（邀请人, 被邀请人）拿到两笔返利。现在先 `select_for_update`
       锁住邀请人（**被加钱的那一方**），判定用的两个查询也在锁里发起。

    被邀请人没有加锁：它在这条路上只是记录里的一个外键，没有任何一行数据被它影响。

    Args:
        user: 充值用户
        recharge_amount: 充值金额
    """
    if not user.invited_by_id:
        return
    inviter_id = user.invited_by_id
    # 惰性取值函数：判定用不到就不查（`every` 一次都不查，金额为 0 时也不查）
    config = InviteConfig.get_config()

    def already_rewarded():
        """这对（邀请人, 被邀请人）是否已有 pending/approved 记录。

        `rejected` 不算 —— 被人工拒绝过的，下次充值还能重新触发一次。
        """
        return InviteReward.objects.filter(
            inviter_id=inviter_id,
            invitee_id=user.pk,
            status__in=COUNTED_STATUSES,
        ).exists()

    def approved_invitees():
        """该邀请人**已审核通过**的去重被邀请人数（`upgrade` 方式的门槛判据）。"""
        return (
            InviteReward.objects
            .filter(inviter_id=inviter_id, status=APPROVED)
            .values('invitee_id')
            .distinct()
            .count()
        )

    with transaction.atomic():
        # 加锁顺序：**先锁邀请人**。`apps/dashboard/views.py::approve_reward` 那条
        # 加钱的路也从这个用户行开始，两条路同序就不会各持一把锁互相等。
        inviter = User.objects.select_for_update().get(pk=inviter_id)
        decision = decide_reward(
            rebate_type=config.rebate_type,
            rebate_ratio=config.rebate_ratio,
            reward_threshold=config.reward_threshold,
            upgrade_threshold=config.upgrade_threshold,
            recharge_amount=recharge_amount,
            already_rewarded=already_rewarded,
            approved_invitees=approved_invitees,
        )
        if not decision.should_reward:
            return
        InviteReward.objects.create(
            inviter=inviter,
            invitee=user,
            recharge_amount=decision.recharge_amount,
            reward_amount=decision.amount,
            status=decision.status,
        )
        if decision.status != APPROVED:
            return
        inviter.balance += decision.amount
        inviter.save(update_fields=['balance'])
        Bill.objects.create(
            user=inviter,
            type='bonus',
            amount=decision.amount,
            balance=inviter.balance,
            description=f'邀请返利（来自{user.username}充值）'
        )
