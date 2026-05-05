"""
URL Configuration for uniTokenHub project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.ai_models.admin import admin_site

urlpatterns = [
    path('admin/', admin_site.urls),
    path('api/users/', include('apps.users.urls')),
    path('api/proxy/', include('apps.api_proxy.urls')),
    path('api/dashboard/', include('apps.dashboard.urls')),
    path('api/models/', include('apps.ai_models.urls')),
    path('api/tickets/', include('apps.tickets.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
