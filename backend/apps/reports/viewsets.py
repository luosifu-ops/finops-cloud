"""工作汇报模块视图：日报 / 周报 / 月报 / 专项复盘 / 点评"""
from datetime import date, timedelta

from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.common.viewsets import ScopeModelViewSet, BizScopeModelViewSet
from apps.common.permissions import IsLeaderOrAbove, report_receivers, is_boss, is_hr_scope
from apps.common.services import notify_user, log_action
from .models import (
    ReportTemplate, DailyReport, WeeklyReport, MonthlyReport, ReviewReport, ReportComment,
    TeamSummary,
)
from .serializers import (
    ReportTemplateSerializer, DailyReportSerializer, WeeklyReportSerializer,
    MonthlyReportSerializer, ReviewReportSerializer, ReportCommentSerializer,
    TeamSummarySerializer,
)
from . import aggregation

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


# ---------------- 汇报自动流转到部门主管（2026-10-29 新增） ----------------
REPORT_FLOW_LINK = {
    "日报": "/reports/daily",
    "周报": "/reports/weekly",
    "月报": "/reports/monthly",
    "专项复盘": "/reports/review",
}


def _report_digest(inst, kind_label):
    """取汇报的可读摘要，用于站内消息正文"""
    who = getattr(getattr(inst, "user", None), "display_name", "") or getattr(
        getattr(inst, "user", None), "username", "")
    if kind_label == "日报":
        when = getattr(inst, "date", "")
        body = getattr(inst, "today_done", "") or ""
    elif kind_label == "周报":
        when = f"{getattr(inst, 'year', '')} 年第 {getattr(inst, 'week', '')} 周"
        body = getattr(inst, "summary", "") or ""
    elif kind_label == "月报":
        when = getattr(inst, "month", "")
        body = getattr(inst, "summary", "") or ""
    else:
        when = getattr(inst, "created_at", "")
        body = getattr(inst, "title", "") or ""
    return who, str(when), str(body)[:200]


def flow_report_to_manager(request, inst, kind_label, link="", owner=None):
    """汇报提交后，自动汇总流转到对应部门主管账号。

    规则：
      1) 接收人 = 提交人所在部门的主管 / 经理（不含本人）
      2) 部门没有主管时，自动升级给老板 / 总经理
      3) 每个接收人收到一条站内消息，点开直达对应汇报列表
      4) 全过程写入操作日志，便于追溯
    """
    owner = owner or getattr(inst, "user", None) or getattr(request, "user", None)
    if not owner:
        return []
    receivers = report_receivers(owner)
    if not receivers:
        return []
    who, when, digest = _report_digest(inst, kind_label)
    title = f"{who} 提交了{kind_label}（{when}）"
    body = digest or "（无正文）"
    for r in receivers:
        notify_user(r, title, body=body, category="REPORT", link=link)
    log_action(
        request, "OTHER", module="工作汇报", obj=inst,
        detail=f"{kind_label}已流转至：" + "、".join(
            [(getattr(x, "display_name", "") or getattr(x, "username", "")) for x in receivers]),
    )
    return receivers


class ReportOwnerMixin:
    """汇报类数据：创建时默认归属当前用户，并自动记录创建人

    2026-10-29 权限专项新增：汇报「提交」后自动汇总流转到对应部门主管账号。
    - 接收人：本部门主管/经理（apps.common.permissions.report_receivers）
    - 方式：站内消息（InboxMessage）+ 操作日志留痕
    - 主管端在「团队汇报」即可看到本部门全部已提交汇报（数据范围由可见性保证）
    """
    flow_label = "工作汇报"
    flow_link = "/reports/daily"

    def _flow_after_submit(self, inst, prev_submitted=False):
        """汇报提交后流转到部门主管（同一份只流转一次），并刷新团队汇总"""
        if not self._is_submitted(inst):
            return
        # 周报/月报没有 status 字段，用填写了总结 + 落提交时间来标记「已提交」
        if not getattr(inst, "submitted_at", None) and hasattr(inst, "submitted_at"):
            try:
                inst.submitted_at = timezone.now()
                inst.save(update_fields=["submitted_at"])
            except Exception:
                pass
        # 2026-10-30 新增：提交后自动汇总到「团队汇报 → 团队汇总」
        # 汇总为幂等重建：首次提交生成、再次提交刷新统计；主管改过的正文不会被覆盖
        try:
            aggregation.aggregate_report(inst, self.flow_label)
        except Exception:
            pass  # 汇总失败不影响汇报保存
        if prev_submitted:
            return
        try:
            flow_report_to_manager(
                self.request, inst, self.flow_label, self.flow_link,
                owner=getattr(inst, "user", None),
            )
        except Exception:
            pass  # 流转失败不影响汇报保存

    def _is_submitted(self, inst):
        # 日报：以状态「已提交」为准
        if hasattr(inst, "status"):
            return getattr(inst, "status", None) == "SUBMITTED"
        # 周报 / 月报：填写了总结即视为提交（表单保存后自动汇总给主管）
        if getattr(inst, "submitted_at", None):
            return True
        return bool((getattr(inst, "summary", "") or "").strip())

    def perform_create(self, serializer):
        user = self.request.user
        if "user" not in serializer.validated_data:
            inst = serializer.save(user=user, created_by=user)
        else:
            inst = serializer.save(created_by=user)
        self._flow_after_submit(inst, prev_submitted=False)

    def perform_update(self, serializer):
        prev = self._is_submitted(serializer.instance)
        inst = serializer.save()
        self._flow_after_submit(inst, prev_submitted=prev)


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
    flow_label = "日报"
    flow_link = REPORT_FLOW_LINK["日报"]
    log_module = "日报"
    scope_by_department = True
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
        was_submitted = bool(report and report.status == "SUBMITTED")
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
        # 2026-10-29 新增：日报提交后自动流转到部门主管账号
        self._flow_after_submit(report, prev_submitted=was_submitted)
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
    flow_label = "周报"
    flow_link = REPORT_FLOW_LINK["周报"]
    log_module = "周报"
    scope_by_department = True
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
        was_submitted = bool(report and report.submitted_at)
        if report:
            for key, value in defaults.items():
                setattr(report, key, value)
        else:
            report = WeeklyReport(user=request.user, year=year, week=week, **defaults)
        # 传 submit=1 视为正式提交，记录提交时间并流转主管
        if str(request.data.get("submit") or "").lower() in ("1", "true", "yes"):
            report.submitted_at = report.submitted_at or timezone.now()
        report.save()
        # 2026-10-29 新增：周报提交后自动流转到部门主管账号
        self._flow_after_submit(report, prev_submitted=was_submitted)
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
    flow_label = "月报"
    flow_link = REPORT_FLOW_LINK["月报"]
    log_module = "月报"
    scope_by_department = True
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
        was_submitted = bool(report and report.submitted_at)
        if report:
            for key, value in defaults.items():
                setattr(report, key, value)
        else:
            report = MonthlyReport(user=request.user, month=month, **defaults)
        # 传 submit=1 视为正式提交，记录提交时间并流转主管
        if str(request.data.get("submit") or "").lower() in ("1", "true", "yes"):
            report.submitted_at = report.submitted_at or timezone.now()
        report.save()
        # 2026-10-29 新增：月报提交后自动流转到部门主管账号
        self._flow_after_submit(report, prev_submitted=was_submitted)
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
    flow_label = "专项复盘"
    flow_link = REPORT_FLOW_LINK["专项复盘"]
    log_module = "专项复盘"
    scope_by_department = True
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


class TeamSummaryViewSet(viewsets.ModelViewSet):
    """团队汇总（2026-10-30 新增）

    - 列表：老板/人事看全量；部门主管看本部门；小组长看本组
    - 编辑：仅可改 title / content，改后标记 is_edited（自动汇总不再覆盖正文）
    - 重新生成：按最新汇报强制重建正文
    - 不支持手工新增 / 删除（由汇报自动生成）
    """
    queryset = TeamSummary.objects.filter(is_deleted=False).select_related(
        "department", "team", "edited_by")
    serializer_class = TeamSummarySerializer
    search_fields = ["title", "content", "period"]
    ordering_fields = ["period", "kind", "updated_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not (is_boss(user) or is_hr_scope(user)):
            if getattr(user, "role", "") == "MANAGER" and user.department_id:
                qs = qs.filter(department_id=user.department_id)
            elif getattr(user, "role", "") == "LEADER" and user.team_id:
                qs = qs.filter(department_id=user.department_id)
            else:
                return qs.none()
        params = self.request.query_params
        if params.get("kind"):
            qs = qs.filter(kind=params["kind"])
        if params.get("period"):
            qs = qs.filter(period=params["period"])
        if params.get("department"):
            qs = qs.filter(department_id=params["department"])
        return qs

    def create(self, request, *args, **kwargs):
        return Response({"detail": "团队汇总由汇报自动生成，不支持手工新增"},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        return Response({"detail": "团队汇总不支持删除"},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def update(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """编辑汇总内容：只有 title / content 可改，改后标记人工编辑"""
        inst = self.get_object()
        data = {}
        for key in ("title", "content"):
            if key in request.data:
                data[key] = request.data.get(key)
        if not data:
            return Response({"detail": "只支持修改标题与汇总内容"},
                            status=status.HTTP_400_BAD_REQUEST)
        for key, value in data.items():
            setattr(inst, key, value)
        inst.is_edited = True
        inst.edited_by = request.user
        inst.edited_at = timezone.now()
        inst.save()
        log_action(request, "UPDATE", module="团队汇总", obj=inst,
                   detail="人工编辑汇总内容（" + "、".join(data.keys()) + "）")
        return Response({"detail": "已保存", "data": TeamSummarySerializer(inst).data})

    @action(detail=True, methods=["post"], permission_classes=[IsLeaderOrAbove])
    def rebuild(self, request, pk=None):
        """按最新汇报强制重建汇总正文（解除人工编辑标记）"""
        inst = self.get_object()
        summary = aggregation.rebuild(inst.kind, inst.period, inst.department,
                                      inst.team, force=True)
        if summary is None:
            return Response({"detail": "重建失败，缺少周期或部门信息"},
                            status=status.HTTP_400_BAD_REQUEST)
        log_action(request, "UPDATE", module="团队汇总", obj=summary, detail="重新生成汇总")
        return Response({"detail": "已重新生成",
                         "data": TeamSummarySerializer(summary).data})

    @action(detail=False, methods=["post"], url_path="rebuild-all")
    def rebuild_all(self, request):
        """按当前账号可见范围，重扫最近汇报并补生成汇总（运维/首次上线用）"""
        made = aggregation.rebuild_all()
        return Response({"detail": f"已重建 {made} 份团队汇总", "count": made})


class ReportCommentViewSet(BizScopeModelViewSet):
    """汇报点评：按 content_type + object_id 过滤，点评人自动填当前用户"""
    queryset = ReportComment.objects.all()
    serializer_class = ReportCommentSerializer
    # 2026-10-29 权限专项：点评按点评人归属收窄（原来任何账号可看全部点评）
    owner_field = "commenter"
    scope_by_department = True
    log_module = "汇报点评"
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
