"""邮件发送工具：直接读取 EmailConfig（数据库）发送邮件，不依赖 Django settings。"""
from __future__ import annotations

import logging
import smtplib
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

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
