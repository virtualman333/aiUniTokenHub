from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuthViewSet, APIKeyViewSet

router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'keys', APIKeyViewSet, basename='keys')

urlpatterns = [
    path('', include(router.urls)),
]
