from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django import forms
from decimal import Decimal
from .models import User, APIKey, UsageLog, Bill, CardPassword, EmailConfig, EmailVerifyCode
from apps.ai_models.admin import admin_site


class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'balance_display', 'is_active', 'created_at', 'add_balance_btn')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'email')
    ordering = ('-created_at',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('角色信息', {'fields': ('role', 'phone')}),
        ('财务信息', {'fields': ('balance',)}),
    )
    
    readonly_fields = ('balance',)
    
    def balance_display(self, obj):
        return f'¥{obj.balance}'
    balance_display.short_description = '余额'
    
    def add_balance_btn(self, obj):
        from django.utils.html import format_html
        url = f'/admin/users/user/{obj.id}/add-balance/'
        return format_html(f'<a class="button" href="{url}" style="background:#79aec8; color:white; padding:3px 10px; border-radius:4px; text-decoration:none;">添加余额</a>')
    add_balance_btn.short_description = '操作'
    
    def add_balance_view(self, request, user_id):
        """添加余额 API 视图（供 Vue 前端调用）"""
        from django.http import JsonResponse
        from django.shortcuts import get_object_or_404
        
        if request.method != 'POST':
            return JsonResponse({'success': False, 'message': '仅支持 POST 请求'})
        
        user = get_object_or_404(User, pk=user_id)
        
        try:
            import json
            data = json.loads(request.body)
            amount = Decimal(str(data.get('amount', '0')))
            description = data.get('description', '').strip()
            
            if amount <= 0:
                return JsonResponse({'success': False, 'message': '金额必须大于0'})
            
            user.balance += amount
            user.save(update_fields=['balance', 'updated_at'])
            
            # 创建交易记录
            bill = Bill.objects.create(
                user=user,
                type='recharge',
                amount=amount,
                balance=user.balance,
                description=description or '管理员手动充值'
            )
            
            return JsonResponse({
                'success': True,
                'message': f'成功充值 ¥{amount}',
                'data': {
                    'user_id': user.id,
                    'username': user.username,
                    'amount': float(amount),
                    'balance': float(user.balance),
                    'bill_id': bill.id
                }
            })
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': '无效的请求数据'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'操作失败：{str(e)}'})
    
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<path:user_id>/add-balance/', 
                 self.admin_site.admin_view(self.add_balance_view), 
                 name='users_user_add_balance'),
        ]
        return custom_urls + urls


class APIKeyAdmin(admin.ModelAdmin):
    list_display = ('key', 'user', 'name', 'is_active', 'expires_at', 'created_at')
    list_filter = ('is_active', 'user')
    search_fields = ('key', 'name')
    ordering = ('-created_at',)


class UsageLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'api_key', 'method', 'endpoint', 'status_code', 'response_time', 'created_at')
    list_filter = ('method', 'status_code')
    search_fields = ('user__username', 'endpoint')
    ordering = ('-created_at',)


class BillAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'amount', 'balance', 'description', 'created_at')
    list_filter = ('type',)
    search_fields = ('user__username', 'description')
    ordering = ('-created_at',)


class CardPasswordAdmin(admin.ModelAdmin):
    list_display = ('code', 'amount', 'status', 'batch_no', 'used_by', 'used_at', 'created_at')
    list_filter = ('status',)
    search_fields = ('code', 'batch_no', 'remark')
    ordering = ('-created_at',)
    readonly_fields = ('used_by', 'used_at')


class EmailConfigAdmin(admin.ModelAdmin):
    """邮箱配置（单例）"""
    list_display = ('id', 'is_enabled', 'smtp_host', 'smtp_port', 'use_ssl', 'use_tls',
                    'smtp_user', 'from_email', 'updated_at')
    fieldsets = (
        ('基础', {
            'fields': ('is_enabled',),
            'description': '关闭后，注册等需要发送邮件的功能将不可用。',
        }),
        ('SMTP 服务器', {
            'fields': ('smtp_host', 'smtp_port', 'use_ssl', 'use_tls',
                       'smtp_user', 'smtp_password',
                       'from_email', 'from_name'),
            'description': '示例：QQ 邮箱 smtp.qq.com:465 SSL；'
                           '163 邮箱 smtp.163.com:465 SSL；'
                           '阿里云邮箱 smtp.qiye.aliyun.com:465 SSL。',
        }),
        ('验证码策略', {
            'fields': ('code_expire_minutes', 'code_resend_seconds', 'daily_limit_per_email'),
        }),
    )

    def has_add_permission(self, request):
        # 单例：如已有则不允许再次新建
        return not EmailConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


class EmailVerifyCodeAdmin(admin.ModelAdmin):
    list_display = ('email', 'code', 'purpose', 'is_used', 'expires_at', 'created_at')
    list_filter = ('purpose', 'is_used')
    search_fields = ('email', 'code')
    ordering = ('-created_at',)
    readonly_fields = ('email', 'code', 'purpose', 'is_used', 'expires_at', 'created_at')

    def has_add_permission(self, request):
        return False


# 注册到自定义 admin_site
admin_site.register(User, UserAdmin)
admin_site.register(APIKey, APIKeyAdmin)
admin_site.register(UsageLog, UsageLogAdmin)
admin_site.register(Bill, BillAdmin)
admin_site.register(CardPassword, CardPasswordAdmin)
admin_site.register(EmailConfig, EmailConfigAdmin)
admin_site.register(EmailVerifyCode, EmailVerifyCodeAdmin)
