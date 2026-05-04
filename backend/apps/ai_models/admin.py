from django.contrib import admin
from .models import AIModel, ModelProvider, ModelCategory


@admin.register(ModelProvider)
class ModelProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'order', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    ordering = ['order', 'id']


@admin.register(ModelCategory)
class ModelCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'order']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    ordering = ['order', 'id']


@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'provider', 'category', 'input_price', 'output_price',
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
        ('定价', {
            'fields': ('input_price', 'output_price')
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
