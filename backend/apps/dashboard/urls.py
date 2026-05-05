from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AdminDashboardViewSet

router = DefaultRouter()
router.register(r'overview', AdminDashboardViewSet, basename='overview')

urlpatterns = [
    path('', include(router.urls)),
    path('users/', AdminDashboardViewSet.as_view({'get': 'list_users'}), name='admin-users-list'),
    path('users/<int:pk>/', AdminDashboardViewSet.as_view({'get': 'retrieve_user', 'patch': 'partial_update_user'}), name='admin-users-detail'),
    path('users/<int:pk>/balance/', AdminDashboardViewSet.as_view({'patch': 'adjust_balance'}), name='admin-users-balance'),
    path('users/<int:pk>/toggle-status/', AdminDashboardViewSet.as_view({'post': 'toggle_status'}), name='admin-users-toggle'),
]
