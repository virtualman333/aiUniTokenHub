"""
管理端：系统设置（邮箱配置 / 测试发送）
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from apps.utils.response import APIResponse
from .models import EmailConfig
from .mailer import send_email, render_verify_code_email, EmailNotConfigured


def _serialize_email_config(cfg: EmailConfig, mask_password: bool = True) -> dict:
    return {
        'is_enabled': cfg.is_enabled,
        'smtp_host': cfg.smtp_host or '',
        'smtp_port': cfg.smtp_port,
        'use_ssl': cfg.use_ssl,
        'use_tls': cfg.use_tls,
        'smtp_user': cfg.smtp_user or '',
        # 密码默认不回显，仅返回是否已设置
        'smtp_password_set': bool(cfg.smtp_password),
        'smtp_password': '' if mask_password else (cfg.smtp_password or ''),
        'from_email': cfg.from_email or '',
        'from_name': cfg.from_name or '',
        'code_expire_minutes': cfg.code_expire_minutes,
        'code_resend_seconds': cfg.code_resend_seconds,
        'daily_limit_per_email': cfg.daily_limit_per_email,
        'updated_at': cfg.updated_at.isoformat() if cfg.updated_at else None,
    }


class SystemSettingsViewSet(viewsets.GenericViewSet):
    """系统设置（管理员）"""
    permission_classes = [IsAuthenticated, IsAdminUser]

    @action(detail=False, methods=['get', 'put'], url_path='email_config')
    def email_config(self, request):
        cfg = EmailConfig.get_config()

        if request.method == 'GET':
            return APIResponse.success(_serialize_email_config(cfg), '获取成功')

        # PUT
        data = request.data or {}
        # 字段白名单
        bool_fields = ['is_enabled', 'use_ssl', 'use_tls']
        str_fields = ['smtp_host', 'smtp_user', 'from_email', 'from_name']
        int_fields = ['smtp_port', 'code_expire_minutes', 'code_resend_seconds', 'daily_limit_per_email']

        for f in bool_fields:
            if f in data:
                setattr(cfg, f, bool(data.get(f)))
        for f in str_fields:
            if f in data:
                setattr(cfg, f, str(data.get(f) or '').strip())
        for f in int_fields:
            if f in data and data.get(f) not in (None, ''):
                try:
                    setattr(cfg, f, int(data.get(f)))
                except (TypeError, ValueError):
                    return APIResponse.error(f'{f} 必须是整数', 400)

        # 密码：只有明确传入非空字符串才更新
        if 'smtp_password' in data:
            new_pwd = data.get('smtp_password')
            if isinstance(new_pwd, str) and new_pwd != '':
                cfg.smtp_password = new_pwd

        # 简单合理性校验
        if cfg.is_enabled:
            if not cfg.smtp_host:
                return APIResponse.error('SMTP 服务器不能为空', 400)
            if not cfg.smtp_user:
                return APIResponse.error('SMTP 用户名不能为空', 400)
            if not cfg.smtp_password:
                return APIResponse.error('SMTP 密码不能为空', 400)
            if not cfg.from_email:
                cfg.from_email = cfg.smtp_user

        cfg.save()
        return APIResponse.success(_serialize_email_config(cfg), '保存成功')

    @action(detail=False, methods=['post'], url_path='email_config/test')
    def email_config_test(self, request):
        """发送测试邮件，使用当前已保存的配置"""
        to_email = (request.data.get('to_email') or '').strip()
        if not to_email or '@' not in to_email:
            return APIResponse.error('请填写有效的收件邮箱', 400)

        cfg = EmailConfig.get_config()
        if not cfg.is_enabled:
            return APIResponse.error('请先启用并保存邮箱配置', 400)

        try:
            subject, html, text = render_verify_code_email(
                code='123456', expire_minutes=cfg.code_expire_minutes or 5,
                purpose='register'
            )
            subject = '【测试】' + subject
            send_email(to_email, subject, html, text)
        except EmailNotConfigured as e:
            return APIResponse.error(str(e), 400)
        except Exception as e:
            return APIResponse.error(f'发送失败：{e}', 500)

        return APIResponse.success(None, f'已发送测试邮件到 {to_email}')
