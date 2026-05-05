from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProxyAccessViewSet

router = DefaultRouter()
router.register(r'forward', ProxyAccessViewSet, basename='forward')

urlpatterns = [
    path('', include(router.urls)),
]
