from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuthViewSet, APIKeyViewSet, BillingViewSet, CardPasswordViewSet

router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'keys', APIKeyViewSet, basename='keys')
router.register(r'billing', BillingViewSet, basename='billing')
router.register(r'cards', CardPasswordViewSet, basename='cards')

urlpatterns = [
    path('', include(router.urls)),
]
