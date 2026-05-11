from django.contrib import admin
from .models import ImageGeneration, GeneratedImage


class GeneratedImageInline(admin.TabularInline):
    model = GeneratedImage
    extra = 0
    readonly_fields = ['image', 'revised_prompt', 'created_at']


@admin.register(ImageGeneration)
class ImageGenerationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'model_code', 'mode', 'status', 'cost', 'created_at']
    list_filter = ['status', 'mode', 'model_code']
    search_fields = ['user__username', 'prompt']
    readonly_fields = ['created_at']
    inlines = [GeneratedImageInline]


@admin.register(GeneratedImage)
class GeneratedImageAdmin(admin.ModelAdmin):
    list_display = ['id', 'generation', 'created_at']
    readonly_fields = ['created_at']
