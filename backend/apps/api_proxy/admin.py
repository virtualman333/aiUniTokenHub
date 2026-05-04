from django.contrib import admin
from .models import APIEndpoint, APICategory


@admin.register(APIEndpoint)
class APIEndpointAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'method', 'path', 'is_active', 'rate_limit', 'price')
    list_filter = ('category', 'method', 'is_active')
    search_fields = ('name', 'path', 'description')
    ordering = ('category', 'path')


@admin.register(APICategory)
class APICategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'order', 'is_active')
    ordering = ('order',)
