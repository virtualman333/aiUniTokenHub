"""邮件发送工具：直接读取 EmailConfig（数据库）发送邮件，不依赖 Django settings。"""
from __future__ import annotations

import logging
import smtplib
import threading
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from django.core.cache import cache

from .models import EmailConfig


logger = logging.getLogger(__name__)


class EmailNotConfigured(Exception):
    pass


def send_email(to_email: str, subject: str, html_body: str, text_body: str | None = None):
    """根据 EmailConfig 发送一封邮件；失败抛异常。"""
    cfg = EmailConfig.get_config()

    if not cfg.is_enabled:
        raise EmailNotConfigured('邮箱服务未启用，请联系管理员在后台配置')
    if not cfg.smtp_host or not cfg.smtp_user or not cfg.smtp_password:
        raise EmailNotConfigured('邮箱服务尚未完成配置')

    from_email = cfg.from_email or cfg.smtp_user
    from_name = cfg.from_name or 'uniTokenHub'

    msg = MIMEMultipart('alternative')
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = formataddr((str(Header(from_name, 'utf-8')), from_email))
    msg['To'] = to_email

    if text_body:
        msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    host = cfg.smtp_host
    port = int(cfg.smtp_port or 0) or (465 if cfg.use_ssl else 25)
    timeout = 15

    try:
        if cfg.use_ssl:
            server = smtplib.SMTP_SSL(host, port, timeout=timeout)
        else:
            server = smtplib.SMTP(host, port, timeout=timeout)
            if cfg.use_tls:
                server.starttls()
        try:
            server.login(cfg.smtp_user, cfg.smtp_password)
            server.sendmail(from_email, [to_email], msg.as_string())
        finally:
            try:
                server.quit()
            except Exception:
                pass
    except smtplib.SMTPException as e:
        logger.error(f'[send_email] SMTP error: {e}')
        raise
    except Exception as e:
        logger.error(f'[send_email] error: {e}')
        raise


def render_verify_code_email(code: str, expire_minutes: int, purpose: str = 'register') -> tuple[str, str, str]:
    """返回 (subject, html, text)"""
    purpose_text = '注册账号' if purpose == 'register' else '重置密码'
    subject = f'【uniTokenHub】{purpose_text}验证码：{code}'
    text = (
        f'您正在{purpose_text}，验证码为：{code}\n'
        f'验证码 {expire_minutes} 分钟内有效，请勿泄露给他人。\n'
        f'如非本人操作，请忽略此邮件。'
    )
    html = f"""<!doctype html>
<html><body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background:#f3f4f6; padding:24px;">
  <div style="max-width:520px; margin:0 auto; background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 4px 16px rgba(0,0,0,.06);">
    <div style="padding:24px 28px; background:linear-gradient(135deg,#10b981,#059669); color:#fff;">
      <h2 style="margin:0; font-size:20px;">uniTokenHub</h2>
      <p style="margin:6px 0 0; font-size:13px; opacity:.85;">{purpose_text}验证码</p>
    </div>
    <div style="padding:28px;">
      <p style="margin:0 0 12px; color:#374151; font-size:14px;">您好，</p>
      <p style="margin:0 0 18px; color:#374151; font-size:14px;">
        您正在 <strong>{purpose_text}</strong>，请在页面输入下方验证码完成操作：
      </p>
      <div style="text-align:center; margin:24px 0;">
        <div style="display:inline-block; padding:14px 28px; background:#ecfdf5; color:#047857; border-radius:8px; font-size:28px; font-weight:700; letter-spacing:6px;">
          {code}
        </div>
      </div>
      <p style="margin:0 0 8px; color:#6b7280; font-size:13px;">验证码 <strong>{expire_minutes}</strong> 分钟内有效，请勿泄露给他人。</p>
      <p style="margin:0; color:#9ca3af; font-size:12px;">如非本人操作，请忽略此邮件。</p>
    </div>
  </div>
</body></html>"""
    return subject, html, text


def _parse_alert_emails(emails_str: str) -> list[str]:
    """解析告警邮箱列表，返回有效的邮箱列表"""
    if not emails_str:
        return []
    return [e.strip() for e in emails_str.split(',') if e.strip() and '@' in e.strip()]


def render_alert_email(status_code: int, model: str, error_msg: str,
                       account_name: str = '', user_id: int = 0,
                       ip: str = '') -> tuple[str, str, str]:
    """渲染告警邮件，返回 (subject, html, text)"""
    subject = f'【uniTokenHub告警】接口异常 - HTTP {status_code}'

    # 状态码颜色映射
    color_map = {
        4: ('#f59e0b', '#fff'),   # 4xx - 黄色警告
        5: ('#ef4444', '#fff'),   # 5xx - 红色严重
    }
    prefix = str(status_code)[0]
    bg_color, text_color = color_map.get(prefix, ('#6b7280', '#fff'))
    level_text = '客户端错误' if prefix == '4' else ('服务器错误' if prefix == '5' else '异常')

    text = (
        f'[uniTokenHub 接口异常告警]\n\n'
        f'状态码: HTTP {status_code}\n'
        f'模型: {model or "-"}\n'
        f'上游账号: {account_name or "-"}\n'
        f'用户ID: {user_id or "-"}\n'
        f'客户端IP: {ip or "-"}\n'
        f'错误信息: {error_msg}\n\n'
        f'请及时检查系统状态。\n'
    )

    html = f"""<!doctype html>
<html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f3f4f6;padding:24px;">
<div style="max-width:560px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,.06);">
  <div style="padding:24px 28px;background:{bg_color};color:{text_color};">
    <h2 style="margin:0;font-size:20px;">uniTokenHub 告警</h2>
    <p style="margin:6px 0 0;font-size:13px;opacity:.85;">API 接口调用异常通知</p>
  </div>
  <div style="padding:28px;">
    <p style="margin:0 0 16px;color:#374151;font-size:14px;">检测到接口调用出现 <strong>{level_text}</strong>，详情如下：</p>

    <table style="width:100%;border-collapse:collapse;font-size:14px;margin-bottom:20px;">
      <tr><td style="padding:8px 12px;background:#f9fafb;color:#6b728b;border-bottom:1px solid #f1f5f9;width:120px;">状态码</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f1f5f9;font-weight:600;color:{bg_color};font-size:18px;">HTTP {status_code}</td></tr>
      <tr><td style="padding:8px 12px;background:#f9fafb;color:#6b728b;border-bottom:1px solid #f1f5f9;">模型</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f1f5f9;"><code style="background:#f1f5f9;padding:2px 6px;border-radius:4px;">{model or '-'}</code></td></tr>
      <tr><td style="padding:8px 12px;background:#f9fafb;color:#6b728b;border-bottom:1px solid #f1f5f9;">上游账号</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f1f5f9;">{account_name or '-'}</td></tr>
      <tr><td style="padding:8px 12px;background:#f9fafb;color:#6b728b;border-bottom:1px solid #f1f5f9;">用户 ID</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f1f5f9;">{user_id or '-'}</td></tr>
      <tr><td style="padding:8px 12px;background:#f9fafb;color:#6b728b;border-bottom:1px solid #f1f5f9;">客户端 IP</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f1f5f9;"><code>{ip or '-'}</code></td></tr>
      <tr><td style="padding:8px 12px;background:#f9fafb;color:#6b728b;vertical-align:top;">错误信息</td>
          <td style="padding:8px 12px;color:#dc2626;word-break:break-all;">{error_msg}</td></tr>
    </table>

    <p style="margin:0;color:#9ca3af;font-size:12px;">此邮件由系统自动发送，请及时检查服务状态。</p>
  </div>
</div>
</body></html>"""
    return subject, html, text


def send_alert_email(status_code: int, model: str = '', error_msg: str = '',
                     account_name: str = '', user_id: int = 0,
                     ip: str = '', override_emails: str | None = None):
    """
    发送告警邮件（带频率限制，异步发送不阻塞主线程）。
    
    Args:
        override_emails: 测试用，强制指定收件人（跳过配置检查）
    """
    cfg = EmailConfig.get_config()

    if not override_emails:
        # 检查是否启用告警
        if not cfg.alert_enabled:
            return
        # 检查邮箱服务是否可用
        if not cfg.is_enabled:
            logger.warning('[send_alert] 邮箱服务未启用，无法发送告警')
            return
        # 解析收件人列表
        recipients = _parse_alert_emails(cfg.alert_emails)
        if not recipients:
            logger.warning('[send_alert] 未配置告警收件人')
            return
    else:
        recipients = [override_emails] if isinstance(override_emails, str) else list(override_emails)

    # 频率限制：同一状态码 + 同一模型，60秒内最多发1次
    cache_key = f'alert_rate:{status_code}:{model}'
    if cache.get(cache_key):
        logger.info(f'[send_alert] 频率限制跳过: key={cache_key}')
        return
    cache.set(cache_key, 1, timeout=60)

    # 渲染邮件内容
    try:
        subject, html_body, text_body = render_alert_email(
            status_code=status_code,
            model=model,
            error_msg=error_msg[:500],  # 截断过长信息
            account_name=account_name,
            user_id=user_id,
            ip=ip,
        )
    except Exception as e:
        logger.error(f'[send_alert] 渲染邮件失败: {e}')
        return

    def _do_send():
        """在子线程中逐个发送"""
        for recipient in recipients:
            try:
                send_email(recipient, subject, html_body, text_body)
                logger.info(f'[send_alert] 已发送告警邮件到 {recipient}')
            except Exception as e:
                logger.error(f'[send_alert] 发送失败 ({recipient}): {e}')

    t = threading.Thread(target=_do_send, daemon=True)
    t.start()
