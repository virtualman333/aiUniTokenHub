from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuthViewSet, APIKeyViewSet, BillingViewSet, CardPasswordViewSet, InviteViewSet
from .views_api_key import APIAccessLogViewSet
from .views_system import SystemSettingsViewSet

router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'keys', APIKeyViewSet, basename='keys')
router.register(r'billing', BillingViewSet, basename='billing')
router.register(r'cards', CardPasswordViewSet, basename='cards')
router.register(r'invite', InviteViewSet, basename='invite')
router.register(r'usage-logs', APIAccessLogViewSet, basename='usage-logs')
router.register(r'admin/system', SystemSettingsViewSet, basename='admin-system')

urlpatterns = [
    path('', include(router.urls)),
]
