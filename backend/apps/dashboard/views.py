from decimal import Decimal

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django.db import models
from django.db.models import Count, Sum, Avg, Q, Exists, OuterRef
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
from apps.users.models import User, APIKey, UsageLog, InviteConfig, InviteReward, Bill
from apps.users.serializers import (
    AdminUserSerializer,
    InviteConfigSerializer,
    InviteRewardSerializer,
)
from apps.api_proxy.models import APIAccessLog
from apps.api_proxy.serializers import APIAccessLogSerializer
from apps.ai_models.models import AIModel, ModelProvider
from apps.ai_models.upstream_models import ModelUpstreamAccount
from apps.utils.response import APIResponse
from .analytics_views import AnalyticsViewSet


class AdminDashboardViewSet(viewsets.GenericViewSet, AnalyticsViewSet):
    """管理端仪表盘"""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_permissions(self):
        if self.action in ["list_users", "retrieve_user"]:
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated(), IsAdminUser()]

    @action(detail=False, methods=["get"])
    def overview(self, request):
        """总览数据"""
        today = timezone.now().date()
        month_start = timezone.make_aware(
            timezone.datetime.combine(
                today.replace(day=1), timezone.datetime.min.time()
            )
        )

        data = {
            "total_users": User.objects.count(),
            "total_apis": AIModel.objects.count(),
            "total_providers": ModelProvider.objects.count(),
            "total_models": AIModel.objects.count(),
            "total_requests": UsageLog.objects.count(),
            "monthly_cost": float(
                Bill.objects.filter(
                    created_at__gte=month_start, type="consume"
                ).aggregate(total=Sum("amount"))["total"]
                or 0
            ),
        }

        return APIResponse.success(data, "获取成功")

    @action(detail=False, methods=["get"])
    def trend(self, request):
        """请求趋势 — 基于 APIAccessLog"""
        days = int(request.query_params.get("days", 7))

        stats = []
        for i in range(days - 1, -1, -1):
            date = timezone.now().date() - timedelta(days=i)
            start = timezone.make_aware(
                timezone.datetime.combine(date, timezone.datetime.min.time())
            )
            end = timezone.make_aware(
                timezone.datetime.combine(date, timezone.datetime.max.time())
            )

            count = APIAccessLog.objects.filter(
                created_at__gte=start, created_at__lte=end
            ).count()
            stats.append({"date": date.strftime("%m-%d"), "count": count})

        return APIResponse.success(stats, "获取成功")

    @action(detail=False, methods=["get"])
    def distribution(self, request):
        """API调用分布"""
        top_apis = (
            APIAccessLog.objects.values("path")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        result = []
        total = sum(item["count"] for item in top_apis) or 1
        for item in top_apis:
            result.append(
                {
                    "name": item["path"],
                    "value": item["count"],
                    "percent": round(item["count"] / total * 100, 1),
                }
            )

        return APIResponse.success(result, "获取成功")

    @action(detail=False, methods=["get"])
    def token_stats(self, request):
        """Token消耗统计"""
        today = timezone.now().date()
        month_start = timezone.make_aware(
            timezone.datetime.combine(
                today.replace(day=1), timezone.datetime.min.time()
            )
        )
        
        # 今日Token消耗
        today_tokens = APIAccessLog.objects.filter(
            created_at__date=today
        ).aggregate(
            total_input=Sum("input_tokens"),
            total_output=Sum("output_tokens"),
            total=Sum("total_tokens")
        )
        
        # 本月Token消耗
        month_tokens = APIAccessLog.objects.filter(
            created_at__gte=month_start
        ).aggregate(
            total_input=Sum("input_tokens"),
            total_output=Sum("output_tokens"),
            total=Sum("total_tokens")
        )
        
        # 按模型统计Token消耗（本月）
        model_tokens = (
            APIAccessLog.objects.filter(created_at__gte=month_start)
            .values("model__name", "model__code")
            .annotate(
                total_tokens=Sum("total_tokens"),
                total_cost=Sum("cost"),
                request_count=Count("id")
            )
            .order_by("-total_tokens")[:10]
        )
        
        model_stats = []
        for item in model_tokens:
            model_stats.append({
                "model_name": item["model__name"] or item["model__code"],
                "total_tokens": item["total_tokens"] or 0,
                "total_cost": float(item["total_cost"] or 0),
                "request_count": item["request_count"]
            })
        
        return APIResponse.success({
            "today": {
                "input_tokens": today_tokens["total_input"] or 0,
                "output_tokens": today_tokens["total_output"] or 0,
                "total_tokens": today_tokens["total"] or 0,
            },
            "month": {
                "input_tokens": month_tokens["total_input"] or 0,
                "output_tokens": month_tokens["total_output"] or 0,
                "total_tokens": month_tokens["total"] or 0,
            },
            "model_stats": model_stats
        }, "获取成功")

    @action(detail=False, methods=["get"])
    def active_users(self, request):
        """活跃用户统计"""
        today = timezone.now().date()
        seven_days_ago = today - timedelta(days=7)
        
        # 今日活跃用户
        today_active = APIAccessLog.objects.filter(
            created_at__date=today,
            user__isnull=False
        ).values("user").distinct().count()
        
        # 7天活跃用户
        week_active = APIAccessLog.objects.filter(
            created_at__date__gte=seven_days_ago,
            user__isnull=False
        ).values("user").distinct().count()
        
        # 活跃用户排行（近7天）
        top_active_users = (
            APIAccessLog.objects.filter(
                created_at__date__gte=seven_days_ago,
                user__isnull=False
            )
            .values("user__username", "user__id")
            .annotate(
                request_count=Count("id"),
                total_tokens=Sum("total_tokens")
            )
            .order_by("-request_count")[:10]
        )
        
        user_stats = []
        for item in top_active_users:
            user_stats.append({
                "username": item["user__username"],
                "request_count": item["request_count"],
                "total_tokens": item["total_tokens"] or 0,
            })
        
        return APIResponse.success({
            "today_active": today_active,
            "week_active": week_active,
            "top_users": user_stats
        }, "获取成功")

    @action(detail=False, methods=["get"])
    def error_analysis(self, request):
        """错误分析"""
        days = int(request.query_params.get("days", 7))
        start_date = timezone.now().date() - timedelta(days=days-1)
        
        # 按日期和状态码统计错误
        error_stats = []
        for i in range(days):
            date = start_date + timedelta(days=i)
            date_start = timezone.make_aware(
                timezone.datetime.combine(date, timezone.datetime.min.time())
            )
            date_end = timezone.make_aware(
                timezone.datetime.combine(date, timezone.datetime.max.time())
            )
            
            total = APIAccessLog.objects.filter(
                created_at__gte=date_start,
                created_at__lte=date_end
            ).count()
            
            errors = APIAccessLog.objects.filter(
                created_at__gte=date_start,
                created_at__lte=date_end,
                response_status__gte=400
            ).count()
            
            error_rate = round((errors / total * 100) if total > 0 else 0, 2)
            
            error_stats.append({
                "date": date.strftime("%m-%d"),
                "total": total,
                "errors": errors,
                "error_rate": error_rate
            })
        
        # 常见错误状态码分布
        error_codes = (
            APIAccessLog.objects.filter(
                created_at__date__gte=start_date,
                response_status__gte=400
            )
            .values("response_status")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )
        
        error_distribution = []
        for item in error_codes:
            error_distribution.append({
                "status": item["response_status"],
                "count": item["count"]
            })
        
        return APIResponse.success({
            "error_trend": error_stats,
            "error_distribution": error_distribution
        }, "获取成功")

    def list_users(self, request):
        """获取用户列表"""
        queryset = User.objects.all().order_by("-created_at")

        # 搜索过滤
        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(username__icontains=search)
                | models.Q(email__icontains=search)
                | models.Q(phone__icontains=search)
            )

        # 角色过滤
        role = request.query_params.get("role")
        if role:
            queryset = queryset.filter(role=role)

        # 状态过滤
        is_active = request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        # 分页
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))
        start = (page - 1) * page_size
        end = start + page_size

        total = queryset.count()
        users = queryset[start:end]
        serializer = AdminUserSerializer(users, many=True)

        return APIResponse.paginated(
            serializer.data, total, page, page_size, "获取成功"
        )

    def retrieve_user(self, request, pk=None):
        """获取单个用户"""
        try:
            user = User.objects.get(pk=pk)
            serializer = AdminUserSerializer(user)
            return APIResponse.success(serializer.data, "获取成功")
        except User.DoesNotExist:
            return APIResponse.error("用户不存在", 404)

    def partial_update_user(self, request, pk=None):
        """更新用户"""
        try:
            user = User.objects.get(pk=pk)
            serializer = AdminUserSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return APIResponse.success(serializer.data, "更新成功")
            return APIResponse.error(str(serializer.errors), 400)
        except User.DoesNotExist:
            return APIResponse.error("用户不存在", 404)

    @action(detail=True, methods=["patch"], url_path="balance")
    def adjust_balance(self, request, pk=None):
        """调整用户余额"""
        try:
            user = User.objects.get(pk=pk)
            amount = request.data.get("amount", 0)
            note = request.data.get("note", "")

            user.balance += Decimal(str(amount))
            user.save()

            return APIResponse.success(
                {
                    "balance": user.balance,
                    "message": f'余额已{"增加" if amount >= 0 else "减少"} {abs(amount)} 元',
                },
                "调整成功",
            )
        except User.DoesNotExist:
            return APIResponse.error("用户不存在", 404)
        except Exception as e:
            return APIResponse.error(str(e), 400)

    @action(detail=True, methods=["post"], url_path="toggle-status")
    def toggle_status(self, request, pk=None):
        """切换用户状态"""
        try:
            user = User.objects.get(pk=pk)
            user.is_active = not user.is_active
            user.save()

            return APIResponse.success(
                {
                    "is_active": user.is_active,
                    "message": f'用户已{"启用" if user.is_active else "禁用"}',
                },
                "操作成功",
            )
        except User.DoesNotExist:
            return APIResponse.error("用户不存在", 404)


class UserDashboardViewSet(viewsets.GenericViewSet):
    """用户端仪表盘"""

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def overview(self, request):
        """用户概览数据"""
        today = timezone.now().date()
        today_start = timezone.make_aware(
            timezone.datetime.combine(today, timezone.datetime.min.time())
        )

        # 获取当前用户的请求日志
        user_logs = APIAccessLog.objects.filter(user=request.user)
        today_logs = user_logs.filter(created_at__gte=today_start)

        # 计算统计数据
        total_requests = user_logs.count()
        today_requests = today_logs.count()

        # 计算成功率
        success_count = user_logs.filter(
            response_status__gte=200, response_status__lt=300
        ).count()
        success_rate = (
            round(success_count / total_requests * 100, 1)
            if total_requests > 0
            else 100
        )

        # 计算Token消耗
        token_stats = user_logs.aggregate(
            total_input_tokens=Sum("input_tokens"),
            total_output_tokens=Sum("output_tokens"),
            total_tokens=Sum("total_tokens")
        )
        total_input_tokens = token_stats["total_input_tokens"] or 0
        total_output_tokens = token_stats["total_output_tokens"] or 0
        total_tokens_consumed = token_stats["total_tokens"] or 0

        data = {
            "total_requests": total_requests,
            "today_requests": today_requests,
            "success_rate": success_rate,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_tokens_consumed,
        }

        return APIResponse.success(data, "获取成功")

    @action(detail=False, methods=["get"])
    def top_apis(self, request):
        """热门API"""
        limit = int(request.query_params.get("limit", 5))

        # 按路径统计调用次数
        top_apis = (
            APIAccessLog.objects.filter(user=request.user)
            .values("path")
            .annotate(count=Count("id"))
            .order_by("-count")[:limit]
        )

        result = [{"name": item["path"], "count": item["count"]} for item in top_apis]

        return APIResponse.success(result, "获取成功")

    @action(detail=False, methods=["get"])
    def debug_db(self, request):
        """诊断端点：检查数据库表结构"""
        from django.db import connection
        
        result = {
            "table_exists": False,
            "columns": [],
            "model_field_exists": False,
            "sample_query": None,
            "error": None,
        }
        
        try:
            with connection.cursor() as cursor:
                # 检查表是否存在
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'api_access_logs'
                    )
                """)
                result["table_exists"] = cursor.fetchone()[0]
                
                # 获取所有列
                cursor.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'api_access_logs'
                """)
                result["columns"] = [
                    {"name": row[0], "type": row[1]}
                    for row in cursor.fetchall()
                ]
                
                # 检查 model_id 列是否存在
                result["model_field_exists"] = any(
                    col["name"] == "model_id" 
                    for col in result["columns"]
                )
                
                # 尝试简单查询
                if result["model_field_exists"]:
                    cursor.execute("""
                        SELECT COUNT(*) 
                        FROM api_access_logs 
                        WHERE model_id IS NOT NULL
                    """)
                    result["sample_query"] = {
                        "model_id_not_null_count": cursor.fetchone()[0]
                    }
                    
        except Exception as e:
            result["error"] = str(e)
            import traceback
            result["error_detail"] = traceback.format_exc()
        
        return APIResponse.success(result, "诊断完成")

    @action(detail=False, methods=["get"])
    def top_models(self, request):
        """热门模型 - 用户最常用的模型统计"""
        try:
            limit = int(request.query_params.get("limit", 5))

            # 按模型统计调用次数和成功率
            top_models_data = (
                APIAccessLog.objects.filter(user=request.user, model__isnull=False)
                .values("model__code", "model__name")
                .annotate(
                    count=Count("id"),
                    success_count=Count("id", filter=Q(response_status__gte=200, response_status__lt=300))
                )
                .order_by("-count")[:limit]
            )

            result = []
            for item in top_models_data:
                model_name = item["model__name"] or item["model__code"]
                count = item["count"]
                success_count = item["success_count"]
                success_rate = round(success_count / count * 100, 1) if count > 0 else 0

                result.append({
                    "name": model_name,
                    "model_code": item["model__code"],
                    "count": count,
                    "success_rate": success_rate,
                })

            # 如果没有数据，返回空列表（前端有模拟数据兜底）
            return APIResponse.success(result, "获取成功")
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"top_models error: {error_detail}")  # 输出到控制台
            return APIResponse.error(f"服务器错误: {str(e)}", 500)

    @action(detail=False, methods=["get"])
    def request_stats(self, request):
        """请求统计（趋势）"""
        days = int(request.query_params.get("days", 7))
        days = min(days, 30)  # 最多30天

        today = timezone.now().date()

        # 按日期分组统计
        stats = []
        for i in range(days - 1, -1, -1):
            date = today - timedelta(days=i)
            date_start = timezone.make_aware(
                timezone.datetime.combine(date, timezone.datetime.min.time())
            )
            date_end = timezone.make_aware(
                timezone.datetime.combine(date, timezone.datetime.max.time())
            )

            day_logs = APIAccessLog.objects.filter(
                user=request.user, created_at__gte=date_start, created_at__lte=date_end
            )

            stats.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "requests": day_logs.count(),
                    "success": day_logs.filter(
                        response_status__gte=200, response_status__lt=300
                    ).count(),
                    "failed": day_logs.filter(
                        Q(response_status__gte=400) | Q(response_status=0)
                    ).count(),
                }
            )

        return APIResponse.success(stats, "获取成功")


class InviteAdminViewSet(viewsets.GenericViewSet):
    """邀请返利管理"""

    permission_classes = [IsAuthenticated, IsAdminUser]

    @action(detail=False, methods=["get", "put"], url_path="config")
    def config(self, request):
        """获取/更新返利配置"""
        config = InviteConfig.get_config()
        if request.method == "GET":
            return APIResponse.success(InviteConfigSerializer(config).data, "获取成功")
        serializer = InviteConfigSerializer(config, data=request.data, partial=True)
        if not serializer.is_valid():
            return APIResponse.error(str(serializer.errors), 400)
        serializer.save()
        return APIResponse.success(serializer.data, "更新成功")

    @action(detail=False, methods=["get"], url_path="rewards")
    def rewards(self, request):
        """获取返利记录列表"""
        queryset = InviteReward.objects.all()
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))
        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        rewards = queryset[start:end]
        serializer = InviteRewardSerializer(rewards, many=True)
        return APIResponse.paginated(serializer.data, total, page, page_size)

    @action(detail=True, methods=["post"], url_path="approve")
    def approve_reward(self, request, pk=None):
        """审核通过返利"""
        try:
            reward = InviteReward.objects.get(pk=pk, status="pending")
        except InviteReward.DoesNotExist:
            return APIResponse.error("返利记录不存在或已处理", 404)
        with models.transaction.atomic():
            reward.status = "approved"
            reward.reviewed_at = timezone.now()
            reward.save()
            inviter = reward.inviter
            inviter.balance += reward.reward_amount
            inviter.save()
            Bill.objects.create(
                user=inviter,
                type="recharge",
                amount=reward.reward_amount,
                balance=inviter.balance,
                description=f"邀请返利审核通过（来自{reward.invitee.username}充值）",
            )
        return APIResponse.success(InviteRewardSerializer(reward).data, "审核通过")

    @action(detail=True, methods=["post"], url_path="reject")
    def reject_reward(self, request, pk=None):
        """审核拒绝返利"""
        try:
            reward = InviteReward.objects.get(pk=pk, status="pending")
        except InviteReward.DoesNotExist:
            return APIResponse.error("返利记录不存在或已处理", 404)
        reward.status = "rejected"
        reward.reviewed_at = timezone.now()
        reward.save()
        return APIResponse.success(InviteRewardSerializer(reward).data, "已拒绝")
