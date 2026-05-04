from django.apps import AppConfig


class ApiProxyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.api_proxy'
    verbose_name = 'API代理'
