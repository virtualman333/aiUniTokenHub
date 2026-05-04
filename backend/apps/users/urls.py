from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuthViewSet, APIKeyViewSet
from .views_admin import AdminUserViewSet

router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'keys', APIKeyViewSet, basename='keys')
router.register(r'', AdminUserViewSet, basename='users')

urlpatterns = [
    path('', include(router.urls)),
]
