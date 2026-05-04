from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, APIKey, UsageLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'email')
    ordering = ('-created_at',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('角色信息', {'fields': ('role', 'phone')}),
    )


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ('key', 'user', 'name', 'is_active', 'expires_at', 'created_at')
    list_filter = ('is_active', 'user')
    search_fields = ('key', 'name')
    ordering = ('-created_at',)


@admin.register(UsageLog)
class UsageLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'api_key', 'method', 'endpoint', 'status_code', 'response_time', 'created_at')
    list_filter = ('method', 'status_code')
    search_fields = ('user__username', 'endpoint')
    ordering = ('-created_at',)
