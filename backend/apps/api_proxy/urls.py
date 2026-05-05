from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import APICategoryViewSet, APIEndpointViewSet, ProxyAccessViewSet

router = DefaultRouter()
router.register(r'categories', APICategoryViewSet, basename='categories')
router.register(r'endpoints', APIEndpointViewSet, basename='endpoints')
router.register(r'forward', ProxyAccessViewSet, basename='forward')

urlpatterns = [
    path('', include(router.urls)),
]
