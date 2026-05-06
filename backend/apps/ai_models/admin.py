from django.contrib import admin
from django.shortcuts import render
from django.urls import path
from .models import AIModel, ModelProvider, ModelCategory


def admin_portal_view(request):
    """管理员入口页面 - 可进入用户端"""
    return render(request, 'admin/portal.html')


class MyAdminSite(admin.AdminSite):
    """自定义管理后台"""
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('portal/', self.admin_view(admin_portal_view), name='admin_portal'),
        ]
        return custom_urls + urls


# 使用自定义 AdminSite
admin_site = MyAdminSite(name='admin')


class ModelProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'order', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    ordering = ['order', 'id']


class ModelCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'order']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    ordering = ['order', 'id']


class AIModelAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'provider', 'category', 'input_price', 'output_price', 'cached_input_price',
        'status', 'is_featured', 'is_new', 'usage_count', 'order', 'created_at'
    ]
    list_filter = ['status', 'is_featured', 'provider', 'category', 'supports_vision']
    search_fields = ['name', 'code', 'description']
    list_editable = ['status', 'is_featured', 'is_new', 'order']
    ordering = ['-is_featured', 'order', '-created_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'code', 'version', 'provider', 'category', 'status')
        }),
        ('定价（元/百万 tokens）', {
            'fields': ('input_price', 'output_price', 'cached_input_price'),
            'description': '价格单位均为 元 / 百万 tokens；缓存命中价为 0 时按输入价计费。',
        }),
        ('功能特性', {
            'fields': ('supports_streaming', 'supports_vision', 'supports_tools', 
                      'supports_json', 'context_window', 'max_tokens')
        }),
        ('描述信息', {
            'fields': ('description', 'capabilities', 'tags')
        }),
        ('状态标记', {
            'fields': ('is_featured', 'is_new', 'order')
        }),
        ('API配置', {
            'fields': ('api_endpoint', 'api_model_id'),
            'classes': ('collapse',)
        }),
    )


# 注册模型到自定义站点
admin_site.register(ModelProvider, ModelProviderAdmin)
admin_site.register(ModelCategory, ModelCategoryAdmin)
admin_site.register(AIModel, AIModelAdmin)
