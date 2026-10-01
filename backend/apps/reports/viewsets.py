"""工作汇报模块视图：日报 / 周报 / 月报 / 专项复盘 / 点评"""
from datetime import date, timedelta

from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.common.viewsets import ScopeModelViewSet
from apps.common.permissions import IsLeaderOrAbove
from .models import (
    ReportTemplate, DailyReport, WeeklyReport, MonthlyReport, ReviewReport, ReportComment,
)
from .serializers import (
    ReportTemplateSerializer, DailyReportSerializer, WeeklyReportSerializer,
    MonthlyReportSerializer, ReviewReportSerializer, ReportCommentSerializer,
)

# 日报可编辑字段
DAILY_FIELDS = ["today_done", "today_data", "problems", "tomorrow_plan",
                "need_help", "remark", "status"]
# 周报可编辑字段
WEEKLY_FIELDS = ["start_date", "end_date", "summary", "data", "next_plan", "problems"]
# 月报可编辑字段
MONTHLY_FIELDS = ["summary", "data", "performance", "target", "next_plan", "self_review"]


def _to_date(value, default=None):
    """把字符串转成日期，失败时返回默认值"""
    if not value:
        return default
    return parse_date(value) or default


def _to_int(value, default=None):
    """把参数转成整数，失败时返回默认值"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class ReportOwnerMixin:
    """汇报类数据：创建时默认归属当前用户，并自动记录创建人"""

    def perform_create(self, serializer):
        user = self.request.user
        if "user" not in serializer.validated_data:
            serializer.save(user=user, created_by=user)
        else:
            serializer.save(created_by=user)


class ReportTemplateViewSet(viewsets.ModelViewSet):
    """汇报模板：按类型(kind)过滤"""
    queryset = ReportTemplate.objects.filter(is_deleted=False)
    serializer_class = ReportTemplateSerializer
    search_fields = ["name"]
    ordering_fields = ["kind", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        kind = params.get("kind")
        if kind:
            qs = qs.filter(kind=kind)
        department = params.get("department")
        if department:
            qs = qs.filter(department_id=department)
        return qs


class DailyReportViewSet(ReportOwnerMixin, ScopeModelViewSet):
    """日报：按员工 / 日期 / 状态过滤，支持 start_date、end_date 区间查询"""
    queryset = DailyReport.objects.filter(is_deleted=False)
    serializer_class = DailyReportSerializer
    owner_field = "user"
    search_fields = ["today_done", "tomorrow_plan", "problems"]
    ordering_fields = ["date", "submitted_at", "score"]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        user_id = params.get("user")
        if user_id:
            qs = qs.filter(user_id=user_id)
        date = _to_date(params.get("date"))
        if date:
            qs = qs.filter(date=date)
        start_date = _to_date(params.get("start_date"))
        if start_date:
            qs = qs.filter(date__gte=start_date)
        end_date = _to_date(params.get("end_date"))
        if end_date:
            qs = qs.filter(date__lte=end_date)
        status_value = params.get("status")
        if status_value:
            qs = qs.filter(status=status_value)
        return qs

    @action(detail=False, methods=["post"], url_path="save-or-update")
    def save_or_update(self, request):
        """按当前用户 + 日期新增或更新日报（date 默认今天）"""
        date = _to_date(request.data.get("date")) or timezone.localdate()
        defaults = {k: request.data.get(k) for k in DAILY_FIELDS if k in request.data}
        report = DailyReport.objects.filter(user=request.user, date=date).first()
        if report:
            for key, value in defaults.items():
                setattr(report, key, value)
            report.status = report.status or "DRAFT"
        else:
            report = DailyReport(user=request.user, date=date,
                                 status=defaults.pop("status", None) or "DRAFT", **defaults)
        if report.status == "SUBMITTED" and not report.submitted_at:
            report.submitted_at = timezone.now()
        report.save()
        return Response({"code": 0, "msg": "保存成功",
                         "data": DailyReportSerializer(report).data})

    @action(detail=False, methods=["get"])
    def my(self, request):
        """我的日报列表"""
        qs = DailyReport.objects.filter(user=request.user, is_deleted=False).order_by("-date")
        start_date = _to_date(request.query_params.get("start_date"))
        if start_date:
            qs = qs.filter(date__gte=start_date)
        end_date = _to_date(request.query_params.get("end_date"))
        if end_date:
            qs = qs.filter(date__lte=end_date)
        return Response({"code": 0, "msg": "ok",
                         "data": DailyReportSerializer(qs, many=True).data})

    @action(detail=False, methods=["get"])
    def team(self, request):
        """团队日报（在数据可见范围内，只返回已提交的）"""
        qs = self.get_queryset().filter(status__in=["SUBMITTED", "REVIEWED"]).order_by("-date")
        return Response({"code": 0, "msg": "ok",
                         "data": DailyReportSerializer(qs, many=True).data})

    @action(detail=True, methods=["post"], permission_classes=[IsLeaderOrAbove])
    def score(self, request, pk=None):
        """主管打分"""
        report = self.get_object()
        score = _to_int(request.data.get("score"))
        if score is None:
            return Response({"code": 1, "msg": "请传入评分 score"},
                            status=status.HTTP_400_BAD_REQUEST)
        report.score = score
        if report.status == "SUBMITTED":
            report.status = "REVIEWED"
        report.save(update_fields=["score", "status"])
        return Response({"code": 0, "msg": "评分成功", "data": {
            "id": report.id, "score": report.score, "status": report.status,
        }})


class WeeklyReportViewSet(ReportOwnerMixin, ScopeModelViewSet):
    """周报：按年 + 周次定位"""
    queryset = WeeklyReport.objects.filter(is_deleted=False)
    serializer_class = WeeklyReportSerializer
    owner_field = "user"
    search_fields = ["summary", "next_plan"]
    ordering_fields = ["year", "week"]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        user_id = params.get("user")
        if user_id:
            qs = qs.filter(user_id=user_id)
        year = _to_int(params.get("year"))
        if year:
            qs = qs.filter(year=year)
        week = _to_int(params.get("week"))
        if week:
            qs = qs.filter(week=week)
        return qs

    @action(detail=False, methods=["post"], url_path="save-or-update")
    def save_or_update(self, request):
        """按当前用户 + 年周新增或更新周报（year、week 默认本周）"""
        today = timezone.localdate()
        iso_year, iso_week, _ = today.isocalendar()
        year = _to_int(request.data.get("year")) or iso_year
        week = _to_int(request.data.get("week")) or iso_week
        defaults = {k: request.data.get(k) for k in WEEKLY_FIELDS if k in request.data}
        # 未传起止日期时，按 ISO 周自动推算（周一 ~ 周日）
        defaults["start_date"] = (_to_date(defaults.get("start_date"))
                                  or date.fromisocalendar(year, week, 1))
        defaults["end_date"] = (_to_date(defaults.get("end_date"))
                                or defaults["start_date"] + timedelta(days=6))

        report = WeeklyReport.objects.filter(user=request.user, year=year, week=week).first()
        if report:
            for key, value in defaults.items():
                setattr(report, key, value)
        else:
            report = WeeklyReport(user=request.user, year=year, week=week, **defaults)
        report.save()
        return Response({"code": 0, "msg": "保存成功",
                         "data": WeeklyReportSerializer(report).data})

    @action(detail=False, methods=["get"])
    def my(self, request):
        """我的周报列表"""
        qs = WeeklyReport.objects.filter(user=request.user, is_deleted=False)
        year = _to_int(request.query_params.get("year"))
        if year:
            qs = qs.filter(year=year)
        return Response({"code": 0, "msg": "ok",
                         "data": WeeklyReportSerializer(qs, many=True).data})


class MonthlyReportViewSet(ReportOwnerMixin, ScopeModelViewSet):
    """月报：按月份(2026-09)定位"""
    queryset = MonthlyReport.objects.filter(is_deleted=False)
    serializer_class = MonthlyReportSerializer
    owner_field = "user"
    search_fields = ["summary", "self_review"]
    ordering_fields = ["month", "performance"]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        user_id = params.get("user")
        if user_id:
            qs = qs.filter(user_id=user_id)
        month = params.get("month")
        if month:
            qs = qs.filter(month=month)
        return qs

    @action(detail=False, methods=["post"], url_path="save-or-update")
    def save_or_update(self, request):
        """按当前用户 + 月份新增或更新月报（month 默认本月）"""
        month = request.data.get("month") or timezone.localdate().strftime("%Y-%m")
        defaults = {k: request.data.get(k) for k in MONTHLY_FIELDS if k in request.data}
        report = MonthlyReport.objects.filter(user=request.user, month=month).first()
        if report:
            for key, value in defaults.items():
                setattr(report, key, value)
        else:
            report = MonthlyReport(user=request.user, month=month, **defaults)
        report.save()
        return Response({"code": 0, "msg": "保存成功",
                         "data": MonthlyReportSerializer(report).data})

    @action(detail=False, methods=["get"])
    def my(self, request):
        """我的月报列表"""
        qs = MonthlyReport.objects.filter(user=request.user, is_deleted=False)
        month = request.query_params.get("month")
        if month:
            qs = qs.filter(month=month)
        return Response({"code": 0, "msg": "ok",
                         "data": MonthlyReportSerializer(qs, many=True).data})


class ReviewReportViewSet(ReportOwnerMixin, ScopeModelViewSet):
    """专项复盘：按类型 + 员工过滤"""
    queryset = ReviewReport.objects.filter(is_deleted=False)
    serializer_class = ReviewReportSerializer
    owner_field = "user"
    search_fields = ["title", "cause", "improvement"]
    ordering_fields = ["created_at", "submitted_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        kind = params.get("kind")
        if kind:
            qs = qs.filter(kind=kind)
        user_id = params.get("user")
        if user_id:
            qs = qs.filter(user_id=user_id)
        return qs

    @action(detail=False, methods=["get"])
    def my(self, request):
        """我的复盘列表"""
        qs = ReviewReport.objects.filter(user=request.user, is_deleted=False)
        kind = request.query_params.get("kind")
        if kind:
            qs = qs.filter(kind=kind)
        return Response({"code": 0, "msg": "ok",
                         "data": ReviewReportSerializer(qs, many=True).data})


class ReportCommentViewSet(viewsets.ModelViewSet):
    """汇报点评：按 content_type + object_id 过滤，点评人自动填当前用户"""
    queryset = ReportComment.objects.all()
    serializer_class = ReportCommentSerializer
    search_fields = ["content"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        content_type = params.get("content_type")
        if content_type:
            qs = qs.filter(content_type=content_type)
        object_id = params.get("object_id")
        if object_id:
            qs = qs.filter(object_id=object_id)
        return qs

    def perform_create(self, serializer):
        """点评人自动记为当前登录用户"""
        serializer.save(commenter=self.request.user)

    @action(detail=False, methods=["get"], url_path="list-by")
    def list_by(self, request):
        """某条汇报的全部点评：/list-by/?content_type=DAILY&object_id=1"""
        content_type = request.query_params.get("content_type")
        object_id = request.query_params.get("object_id")
        if not content_type or not object_id:
            return Response({"code": 1, "msg": "请传入 content_type 和 object_id"},
                            status=status.HTTP_400_BAD_REQUEST)
        qs = ReportComment.objects.filter(
            content_type=content_type, object_id=object_id).order_by("-created_at")
        return Response({"code": 0, "msg": "ok",
                         "data": ReportCommentSerializer(qs, many=True).data})
