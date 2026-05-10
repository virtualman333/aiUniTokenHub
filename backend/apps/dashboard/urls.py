from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AdminDashboardViewSet, InviteAdminViewSet, UserDashboardViewSet

router = DefaultRouter()
router.register(r"overview", AdminDashboardViewSet, basename="overview")

urlpatterns = [
    # 管理端路由（需要在 router 之前定义，避免被覆盖）
    # 流量统计路由
    path(
        "admin/analytics/summary/",
        AdminDashboardViewSet.as_view({"get": "analytics_summary"}),
        name="admin-analytics-summary",
    ),
    path(
        "admin/analytics/trend/",
        AdminDashboardViewSet.as_view({"get": "analytics_trend"}),
        name="admin-analytics-trend",
    ),
    path(
        "admin/analytics/pages/",
        AdminDashboardViewSet.as_view({"get": "analytics_pages"}),
        name="admin-analytics-pages",
    ),
    path(
        "admin/analytics/sources/",
        AdminDashboardViewSet.as_view({"get": "analytics_sources"}),
        name="admin-analytics-sources",
    ),
    path(
        "admin/analytics/realtime/",
        AdminDashboardViewSet.as_view({"get": "analytics_realtime"}),
        name="admin-analytics-realtime",
    ),
    # 访问记录分页列表（具体网页IP、PV、UV查询）
    path(
        "admin/analytics/records/",
        AdminDashboardViewSet.as_view({"get": "analytics_records"}),
        name="admin-analytics-records",
    ),
    # 用户管理路由
    path(
        "admin/users/",
        AdminDashboardViewSet.as_view({"get": "list_users"}),
        name="admin-users-list",
    ),
    path(
        "admin/users/<int:pk>/",
        AdminDashboardViewSet.as_view(
            {"get": "retrieve_user", "patch": "partial_update_user"}
        ),
        name="admin-users-detail",
    ),
    path(
        "admin/users/<int:pk>/balance/",
        AdminDashboardViewSet.as_view({"patch": "adjust_balance"}),
        name="admin-users-balance",
    ),
    path(
        "admin/users/<int:pk>/toggle-status/",
        AdminDashboardViewSet.as_view({"post": "toggle_status"}),
        name="admin-users-toggle",
    ),
    # 邀请返利管理
    path(
        "admin/invite/config/",
        InviteAdminViewSet.as_view({"get": "config", "put": "config"}),
        name="admin-invite-config",
    ),
    path(
        "admin/invite/rewards/",
        InviteAdminViewSet.as_view({"get": "rewards"}),
        name="admin-invite-rewards",
    ),
    path(
        "admin/invite/rewards/<int:pk>/approve/",
        InviteAdminViewSet.as_view({"post": "approve_reward"}),
        name="admin-invite-approve",
    ),
    path(
        "admin/invite/rewards/<int:pk>/reject/",
        InviteAdminViewSet.as_view({"post": "reject_reward"}),
        name="admin-invite-reject",
    ),
    path(
        "admin/trend/",
        AdminDashboardViewSet.as_view({"get": "trend"}),
        name="admin-trend",
    ),
    path(
        "admin/distribution/",
        AdminDashboardViewSet.as_view({"get": "distribution"}),
        name="admin-distribution",
    ),
    path(
        "admin/token-stats/",
        AdminDashboardViewSet.as_view({"get": "token_stats"}),
        name="admin-token-stats",
    ),
    path(
        "admin/active-users/",
        AdminDashboardViewSet.as_view({"get": "active_users"}),
        name="admin-active-users",
    ),
    path(
        "admin/error-analysis/",
        AdminDashboardViewSet.as_view({"get": "error_analysis"}),
        name="admin-error-analysis",
    ),
    path(
        "admin/overview/",
        AdminDashboardViewSet.as_view({"get": "overview"}),
        name="admin-overview",
    ),
    # 用户端路由
    path(
        "user/overview/",
        UserDashboardViewSet.as_view({"get": "overview"}),
        name="user-overview",
    ),
    path(
        "user/top-apis/",
        UserDashboardViewSet.as_view({"get": "top_apis"}),
        name="user-top-apis",
    ),
    path(
        "user/top-models/",
        UserDashboardViewSet.as_view({"get": "top_models"}),
        name="user-top-models",
    ),
    path(
        "user/request-stats/",
        UserDashboardViewSet.as_view({"get": "request_stats"}),
        name="user-request-stats",
    ),
    # router 路由（放最后，作为默认的 overview 路由）
    path("", include(router.urls)),
]
