from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AdminDashboardViewSet, InviteAdminViewSet

router = DefaultRouter()
router.register(r'overview', AdminDashboardViewSet, basename='overview')

urlpatterns = [
    # 自定义路由（优先匹配）
    path('users/', AdminDashboardViewSet.as_view({'get': 'list_users'}), name='admin-users-list'),
    path('users/<int:pk>/', AdminDashboardViewSet.as_view({'get': 'retrieve_user', 'patch': 'partial_update_user'}), name='admin-users-detail'),
    path('users/<int:pk>/balance/', AdminDashboardViewSet.as_view({'patch': 'adjust_balance'}), name='admin-users-balance'),
    path('users/<int:pk>/toggle-status/', AdminDashboardViewSet.as_view({'post': 'toggle_status'}), name='admin-users-toggle'),
    # 邀请返利管理
    path('invite/config/', InviteAdminViewSet.as_view({'get': 'config', 'put': 'config'}), name='admin-invite-config'),
    path('invite/rewards/', InviteAdminViewSet.as_view({'get': 'rewards'}), name='admin-invite-rewards'),
    path('invite/rewards/<int:pk>/approve/', InviteAdminViewSet.as_view({'post': 'approve_reward'}), name='admin-invite-approve'),
    path('invite/rewards/<int:pk>/reject/', InviteAdminViewSet.as_view({'post': 'reject_reward'}), name='admin-invite-reject'),
    # router 路由
    path('', include(router.urls)),
]
