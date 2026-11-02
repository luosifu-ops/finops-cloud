"""运营部：视图集"""
import calendar
from datetime import date, datetime, timedelta

from django.db.models import Q, Count, Sum
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.permissions import visible_user_ids, is_boss
from apps.common.viewsets import ScopeModelViewSet, BizScopeModelViewSet
from django.contrib.auth import get_user_model
User = get_user_model()
from .models import (
    AdPlatform, AdAccount, AdCampaign, AdDailyStat, AdCreative,
    ContentPost, ContentStat, ChannelBudget, OpsDailyReport, CostRecord,
)
from .serializers import (
    AdPlatformSerializer, AdAccountSerializer, AdCampaignSerializer,
    AdDailyStatSerializer, AdCreativeSerializer, ContentPostSerializer,
    ContentStatSerializer, ChannelBudgetSerializer, OpsDailyReportSerializer,
    AnchorDailyReportSerializer, LeadLedgerSerializer, AnchorAdStatSerializer,
    CostRecordSerializer,
)


# ---------------- 公共小工具 ----------------
def apply_filters(qs, request, mapping):
    """按查询参数过滤，mapping 为 {参数名: ORM 字段路径}"""
    for key, field in mapping.items():
        value = request.query_params.get(key)
        if value not in (None, "", "undefined"):
            qs = qs.filter(**{field: value})
    return qs


def parse_date(value):
    """把 YYYY-MM-DD 字符串转成 date，失败返回 None"""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def month_range(month):
    """2026-09 -> (date(2026,9,1), date(2026,9,30))"""
    if not month:
        today = timezone.localdate()
        month = today.strftime("%Y-%m")
    try:
        year, mon = int(month[:4]), int(month[5:7])
    except (ValueError, IndexError):
        today = timezone.localdate()
        year, mon = today.year, today.month
    last_day = calendar.monthrange(year, mon)[1]
    return date(year, mon, 1), date(year, mon, last_day)


def to_float(value):
    """Decimal / None 统一转 float"""
    return float(value or 0)


def to_int(value, default=0):
    """字符串转整数"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def div(numerator, denominator, digits=2):
    """安全除法，分母为 0 时返回 0"""
    denominator = float(denominator or 0)
    if not denominator:
        return 0
    return round(float(numerator or 0) / denominator, digits)


def to_rate(numerator, denominator):
    """百分比，分母为 0 时返回 0"""
    return div(numerator, denominator * 0.01, 1) if denominator else 0


def is_big_boss(user):
    """老板/超管：看全部经营数据。
    2026-10-29 权限专项：HR 不再自动获得全公司业务数据。"""
    return is_boss(user)


def paginate(view, qs, serializer_class):
    """额外 action 的统一分页输出"""
    page = view.paginate_queryset(qs)
    if page is not None:
        return view.get_paginated_response(serializer_class(page, many=True).data)
    return Response({"code": 0, "msg": "ok", "data": serializer_class(qs, many=True).data})


def resolve_platform(value):
    """平台可以传 id，也可以传编码或名称"""
    if value in (None, ""):
        return None
    if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
        return AdPlatform.objects.filter(id=int(value), is_deleted=False).first()
    return AdPlatform.objects.filter(
        Q(code=value) | Q(name=value), is_deleted=False).first()


def resolve_instance(model, value):
    """按主键取对象，非法值返回 None"""
    if value in (None, ""):
        return None
    return model.objects.filter(id=to_int(value, -1)).first()


# 聚合字段
# 别名统一加 sum_ 前缀，避免与模型字段名冲突
SUM_FIELDS = {
    "sum_cost": Sum("cost"),
    "sum_impression": Sum("impression"),
    "sum_click": Sum("click"),
    "sum_lead_count": Sum("lead_count"),
    "sum_valid_lead": Sum("valid_lead"),
    "sum_wechat_added": Sum("wechat_added"),
    "sum_visit_count": Sum("visit_count"),
    "sum_deal_count": Sum("deal_count"),
    "sum_deal_amount": Sum("deal_amount"),
}


def aggregate_row(row):
    """把聚合结果统一转 float，并去掉 sum_ 前缀"""
    return {key[4:]: to_float(row.get(key)) for key in SUM_FIELDS}


def with_metrics(data):
    """补充 CPL / CAC / ROI / 线索有效率"""
    data["cpl"] = div(data["cost"], data["lead_count"])
    data["cac"] = div(data["cost"], data["deal_count"])
    data["roi"] = div(data["deal_amount"], data["cost"])
    data["lead_valid_rate"] = to_rate(data["valid_lead"], data["lead_count"])
    data["click_rate"] = to_rate(data["click"], data["impression"])
    return data


# ---------------- 投放平台 ----------------
class AdPlatformViewSet(viewsets.ModelViewSet):
    """投放平台"""
    queryset = AdPlatform.objects.filter(is_deleted=False)
    serializer_class = AdPlatformSerializer
    search_fields = ["name", "code", "contact"]
    ordering_fields = ["id", "name"]

    def get_queryset(self):
        qs = super().get_queryset()
        return apply_filters(qs, self.request, {"code": "code", "has_api": "has_api"})

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# ---------------- 广告账户 ----------------
class AdAccountViewSet(BizScopeModelViewSet):
    """广告账户"""
    queryset = AdAccount.objects.filter(is_deleted=False)
    serializer_class = AdAccountSerializer
    owner_field = "owner"
    scope_by_department = True
    log_module = "广告账户"
    search_fields = ["name", "account_id"]
    ordering_fields = ["created_at", "balance"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = apply_filters(qs, self.request, {
            "platform": "platform_id",
            "status": "status",
            "owner": "owner_id",
        })
        user = self.request.user
        if not is_big_boss(user):
            ids = list(visible_user_ids(user))
            qs = qs.filter(Q(owner__in=ids) | Q(owner__isnull=True))
        return qs

    def perform_create(self, serializer):
        data = serializer.validated_data
        if data.get("owner") is None and self.request.user.role == "EMPLOYEE":
            serializer.save(owner=self.request.user, created_by=self.request.user)
        else:
            serializer.save(created_by=self.request.user)


# ---------------- 推广计划 ----------------
class AdCampaignViewSet(BizScopeModelViewSet):
    """推广计划"""
    queryset = AdCampaign.objects.filter(is_deleted=False)
    serializer_class = AdCampaignSerializer
    # 计划跟随所属广告账户的负责人
    owner_field = "account__owner"
    scope_by_department = True
    log_module = "推广计划"
    search_fields = ["name", "campaign_id", "biz_line", "city"]
    ordering_fields = ["created_at", "start_date"]

    def get_queryset(self):
        qs = super().get_queryset()
        return apply_filters(qs, self.request, {
            "account": "account_id",
            "biz_line": "biz_line",
            "status": "status",
            "platform": "account__platform_id",
        })

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# ---------------- 每日投放数据 ----------------
class AdDailyStatViewSet(BizScopeModelViewSet):
    """每日投放数据（核心）"""
    queryset = AdDailyStat.objects.all()
    serializer_class = AdDailyStatSerializer
    # 数据归属：录入人 / 所属账户负责人
    owner_field = "operator"
    scope_fields = ("operator", "account__owner")
    scope_by_department = True
    log_module = "每日投放数据"
    ordering_fields = ["date", "cost", "lead_count", "deal_amount"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = apply_filters(qs, self.request, {
            "platform": "platform_id",
            "account": "account_id",
            "campaign": "campaign_id",
        })
        start = parse_date(self.request.query_params.get("start_date"))
        end = parse_date(self.request.query_params.get("end_date"))
        if start:
            qs = qs.filter(date__gte=start)
        if end:
            qs = qs.filter(date__lte=end)
        return qs

    def perform_create(self, serializer):
        serializer.save(operator=self.request.user)

    def perform_update(self, serializer):
        serializer.save(operator=self.request.user)

    @action(detail=False, methods=["post"], url_path="batch-input")
    def batch_input(self, request):
        """批量录入/导入投放数据：date + items 数组，按唯一键去重"""
        stat_date = parse_date(request.data.get("date"))
        items = request.data.get("items") or []
        if not stat_date or not items:
            return Response({"code": 1, "msg": "参数 date 和 items 必填"},
                            status=status.HTTP_400_BAD_REQUEST)
        created = updated = skipped = 0
        for item in items:
            platform = resolve_platform(item.get("platform"))
            if not platform:
                skipped += 1
                continue
            account = resolve_instance(AdAccount, item.get("account"))
            campaign = resolve_instance(AdCampaign, item.get("campaign"))
            defaults = {
                "cost": item.get("cost", 0),
                "cost_input": item.get("cost_input", 0),
                "impression": to_int(item.get("impression")),
                "click": to_int(item.get("click")),
                "lead_count": to_int(item.get("lead_count")),
                "valid_lead": to_int(item.get("valid_lead")),
                "phone_added": to_int(item.get("phone_added")),
                "wechat_added": to_int(item.get("wechat_added")),
                "visit_count": to_int(item.get("visit_count")),
                "deal_count": to_int(item.get("deal_count")),
                "deal_amount": item.get("deal_amount", 0),
                "remark": item.get("remark", ""),
                "operator": request.user,
            }
            click = defaults["click"]
            impression = defaults["impression"]
            defaults["click_rate"] = to_rate(click, impression)
            defaults["avg_click_cost"] = div(defaults["cost"], click)
            _, is_new = AdDailyStat.objects.update_or_create(
                platform=platform, account=account, campaign=campaign,
                date=stat_date, defaults=defaults,
            )
            if is_new:
                created += 1
            else:
                updated += 1
        return Response({"code": 0, "msg": "ok",
                         "data": {"date": str(stat_date), "created": created,
                                  "updated": updated, "skipped": skipped}})

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """总览：消耗/线索/加微/成交/成交金额/CPL/CAC/ROI"""
        qs = self.get_queryset()
        row = qs.aggregate(**SUM_FIELDS)
        data = with_metrics(aggregate_row(row))
        data["days"] = qs.values("date").distinct().count()
        return Response({"code": 0, "msg": "ok", "data": data})

    @action(detail=False, methods=["get"], url_path="platform-compare")
    def platform_compare(self, request):
        """各平台对比"""
        qs = self.get_queryset()
        rows = qs.values("platform_id", "platform__name").annotate(**SUM_FIELDS)
        data = []
        for row in rows:
            item = aggregate_row(row)
            item["platform_id"] = row["platform_id"]
            item["platform_name"] = row["platform__name"]
            data.append(with_metrics(item))
        data.sort(key=lambda x: x["cost"], reverse=True)
        return Response({"code": 0, "msg": "ok", "data": data})

    @action(detail=False, methods=["get"])
    def trend(self, request):
        """按天趋势（供前端画折线图）"""
        qs = self.get_queryset()
        rows = qs.values("date").annotate(**SUM_FIELDS).order_by("date")
        data = []
        for row in rows:
            item = aggregate_row(row)
            item["date"] = row["date"].strftime("%Y-%m-%d") if row["date"] else ""
            data.append(item)
        return Response({"code": 0, "msg": "ok", "data": data})

    @action(detail=False, methods=["get"])
    def funnel(self, request):
        """转化漏斗：展现→点击→线索→有效线索→加微→到店→成交"""
        qs = self.get_queryset()
        row = qs.aggregate(**SUM_FIELDS)
        data = aggregate_row(row)
        steps = [
            ("impression", "展现"),
            ("click", "点击"),
            ("lead_count", "线索"),
            ("valid_lead", "有效线索"),
            ("wechat_added", "加微"),
            ("visit_count", "到店/邀约"),
            ("deal_count", "成交"),
        ]
        top = data["impression"]
        items = []
        previous = None
        for index, (key, name) in enumerate(steps):
            items.append({
                "key": key,
                "name": name,
                "count": int(data[key]),
                "rate_from_top": to_rate(data[key], top) if index else 100,
                "rate_from_prev": 100 if index == 0 else to_rate(data[key], previous),
            })
            previous = data[key]
        return Response({"code": 0, "msg": "ok", "data": items})

    @action(detail=False, methods=["get"], url_path="budget-vs-actual")
    def budget_vs_actual(self, request):
        """预算 vs 实际：对比 ChannelBudget 与实际消耗/线索/成交"""
        month = request.query_params.get("month")
        start, end = month_range(month)
        month = start.strftime("%Y-%m")
        budgets = ChannelBudget.objects.filter(is_deleted=False, month=month)
        actual_rows = self.get_queryset().filter(
            date__gte=start, date__lte=end
        ).values("platform_id").annotate(**SUM_FIELDS)
        actual_map = {row["platform_id"]: aggregate_row(row) for row in actual_rows}
        data = []
        for budget in budgets:
            actual = actual_map.get(budget.platform_id, {k: 0 for k in SUM_FIELDS})
            data.append({
                "platform_id": budget.platform_id,
                "platform_name": budget.platform.name,
                "budget": to_float(budget.budget),
                "lead_target": budget.lead_target,
                "deal_target": budget.deal_target,
                "actual_cost": actual.get("cost", 0),
                "actual_lead": int(actual.get("lead_count", 0)),
                "actual_deal": int(actual.get("deal_count", 0)),
                "cost_rate": to_rate(actual.get("cost", 0), budget.budget),
                "lead_rate": to_rate(actual.get("lead_count", 0), budget.lead_target),
                "deal_rate": to_rate(actual.get("deal_count", 0), budget.deal_target),
            })
        total = {
            "budget": round(sum(i["budget"] for i in data), 2),
            "actual_cost": round(sum(i["actual_cost"] for i in data), 2),
            "lead_target": sum(i["lead_target"] for i in data),
            "actual_lead": sum(i["actual_lead"] for i in data),
            "deal_target": sum(i["deal_target"] for i in data),
            "actual_deal": sum(i["actual_deal"] for i in data),
        }
        total["cost_rate"] = to_rate(total["actual_cost"], total["budget"])
        total["lead_rate"] = to_rate(total["actual_lead"], total["lead_target"])
        total["deal_rate"] = to_rate(total["actual_deal"], total["deal_target"])
        return Response({"code": 0, "msg": "ok",
                         "data": {"month": month, "total": total, "items": data}})


# ---------------- 投放素材 ----------------
class AdCreativeViewSet(viewsets.ModelViewSet):
    """投放素材"""
    queryset = AdCreative.objects.filter(is_deleted=False)
    serializer_class = AdCreativeSerializer
    search_fields = ["name", "copy"]
    ordering_fields = ["created_at", "lead_count", "cost"]

    def get_queryset(self):
        qs = super().get_queryset()
        return apply_filters(qs, self.request, {
            "platform": "platform_id",
            "kind": "kind",
            "online": "online",
        })

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# ---------------- 内容作品 ----------------
class ContentPostViewSet(BizScopeModelViewSet):
    """内容作品"""
    queryset = ContentPost.objects.filter(is_deleted=False)
    serializer_class = ContentPostSerializer
    owner_field = "author"
    scope_by_department = True
    log_module = "内容作品"
    search_fields = ["title", "topic", "script"]
    ordering_fields = ["publish_at", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = apply_filters(qs, self.request, {
            "platform": "platform",
            "status": "status",
            "author": "author_id",
            "kind": "kind",
        })
        start = parse_date(self.request.query_params.get("start_date"))
        end = parse_date(self.request.query_params.get("end_date"))
        if start:
            qs = qs.filter(publish_at__date__gte=start)
        if end:
            qs = qs.filter(publish_at__date__lte=end)
        return qs

    def perform_create(self, serializer):
        data = serializer.validated_data
        if data.get("author") is None and self.request.user.role == "EMPLOYEE":
            serializer.save(author=self.request.user, created_by=self.request.user)
        else:
            serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["get"])
    def my(self, request):
        """我产出的内容"""
        qs = self.get_queryset().filter(author=request.user)
        return paginate(self, qs, ContentPostSerializer)

    @action(detail=False, methods=["get"], url_path="stat-summary")
    def stat_summary(self, request):
        """内容总数据：发布数、总播放、总点赞、总私信、总线索"""
        start = parse_date(request.query_params.get("start_date"))
        end = parse_date(request.query_params.get("end_date"))
        posts = self.get_queryset()
        stats = ContentStat.objects.filter(post_id__in=posts.values("id"))
        if start:
            stats = stats.filter(stat_date__gte=start)
        if end:
            stats = stats.filter(stat_date__lte=end)
        row = stats.aggregate(
            view=Sum("view"), like=Sum("like"), comment=Sum("comment"),
            share=Sum("share"), collect=Sum("collect"), follow=Sum("follow"),
            private_msg=Sum("private_msg"), lead_count=Sum("lead_count"),
        )
        return Response({"code": 0, "msg": "ok", "data": {
            "post_count": posts.count(),
            "published_count": posts.filter(status="PUBLISHED").count(),
            "view": to_int(row["view"]),
            "like": to_int(row["like"]),
            "comment": to_int(row["comment"]),
            "share": to_int(row["share"]),
            "collect": to_int(row["collect"]),
            "follow": to_int(row["follow"]),
            "private_msg": to_int(row["private_msg"]),
            "lead_count": to_int(row["lead_count"]),
        }})


# ---------------- 内容数据 ----------------
class ContentStatViewSet(BizScopeModelViewSet):
    """内容数据"""
    queryset = ContentStat.objects.all()
    serializer_class = ContentStatSerializer
    # 数据跟随所属作品作者
    owner_field = "post__author"
    scope_by_department = True
    log_module = "内容数据"
    ordering_fields = ["stat_date", "view"]

    def get_queryset(self):
        qs = super().get_queryset()
        return apply_filters(qs, self.request, {"post": "post_id"})

    @action(detail=False, methods=["post"], url_path="batch-input")
    def batch_input(self, request):
        """批量录入内容数据：post_id + items 数组（或 items 内自带 post_id）"""
        default_post_id = request.data.get("post_id")
        items = request.data.get("items") or []
        if not items:
            return Response({"code": 1, "msg": "参数 items 必填"},
                            status=status.HTTP_400_BAD_REQUEST)
        stat_date = parse_date(request.data.get("date"))
        created = updated = skipped = 0
        for item in items:
            post_id = item.get("post_id") or default_post_id
            row_date = parse_date(item.get("stat_date")) or stat_date
            if not post_id or not row_date:
                skipped += 1
                continue
            defaults = {
                "view": to_int(item.get("view")),
                "like": to_int(item.get("like")),
                "comment": to_int(item.get("comment")),
                "share": to_int(item.get("share")),
                "collect": to_int(item.get("collect")),
                "follow": to_int(item.get("follow")),
                "private_msg": to_int(item.get("private_msg")),
                "lead_count": to_int(item.get("lead_count")),
            }
            _, is_new = ContentStat.objects.update_or_create(
                post_id=post_id, stat_date=row_date, defaults=defaults
            )
            if is_new:
                created += 1
            else:
                updated += 1
        return Response({"code": 0, "msg": "ok",
                         "data": {"created": created, "updated": updated, "skipped": skipped}})


# ---------------- 渠道预算 ----------------
class ChannelBudgetViewSet(BizScopeModelViewSet):
    """渠道预算"""
    queryset = ChannelBudget.objects.filter(is_deleted=False)
    serializer_class = ChannelBudgetSerializer
    owner_field = "created_by"
    log_module = "渠道预算"
    ordering_fields = ["month", "budget"]

    def get_queryset(self):
        qs = super().get_queryset()
        return apply_filters(qs, self.request, {
            "month": "month",
            "platform": "platform_id",
        })

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        """预算审批联动：员工改预算 → 进入待审批（budget 不变）；管理层直接生效"""
        u = self.request.user
        is_mgr = u.is_superuser or getattr(u, "role", "") in ("BOSS", "MANAGER")
        new_budget = serializer.validated_data.get("budget")
        if not is_mgr and new_budget is not None:
            old = ChannelBudget.objects.get(pk=serializer.instance.pk)
            if str(new_budget) != str(old.budget):
                instance = serializer.save(budget=old.budget, approve_status="PENDING",
                                           pending_budget=new_budget,
                                           pending_reason=serializer.validated_data.get("remark", old.remark),
                                           reject_reason="")
                from apps.common.services import log_action, notify_user
                log_action(self.request, "UPDATE", module="渠道预算", obj=instance,
                           detail=f"申请调整预算 {old.budget} → {new_budget}，待审批")
                bosses = User.objects.filter(role="BOSS", is_active=True)
                for b in bosses:
                    notify_user(b, "预算调整待审批",
                                f"{u.display_name or u.username} 申请将 {instance.month} "
                                f"{instance.platform_name if hasattr(instance.platform, 'name') else instance.platform_id} "
                                f"预算从 {old.budget} 调整为 {new_budget}，请到预算管理审批。",
                                category="APPROVAL", link="/ops/budgets")
                return
        serializer.save()

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """审批通过：pending_budget 落地为生效预算（仅管理层）"""
        if not (request.user.is_superuser or getattr(request.user, "role", "") in ("BOSS", "MANAGER")):
            return Response({"code": 1, "msg": "仅管理层可审批预算"}, status=status.HTTP_403_FORBIDDEN)
        b = self.get_object()
        if b.approve_status != "PENDING" or b.pending_budget is None:
            return Response({"code": 1, "msg": "该预算没有待审批的调整"}, status=status.HTTP_400_BAD_REQUEST)
        old = b.budget
        b.budget = b.pending_budget
        b.approve_status = "APPROVED"
        b.reviewer = request.user
        b.reviewed_at = timezone.now()
        b.save(update_fields=["budget", "approve_status", "reviewer", "reviewed_at"])
        from apps.common.services import log_action, notify_user
        log_action(request, "APPROVE", module="渠道预算", obj=b, detail=f"预算 {old} → {b.budget} 审批通过")
        if b.created_by:
            notify_user(b.created_by, "预算调整已通过",
                        f"{b.month} {b.platform.name} 预算 {old} → {b.budget} 已生效。",
                        category="APPROVAL", link="/ops/budgets")
        return Response({"code": 0, "msg": f"已通过，预算 {old} → {b.budget} 生效"})

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """审批驳回：预算维持原值"""
        if not (request.user.is_superuser or getattr(request.user, "role", "") in ("BOSS", "MANAGER")):
            return Response({"code": 1, "msg": "仅管理层可审批预算"}, status=status.HTTP_403_FORBIDDEN)
        b = self.get_object()
        if b.approve_status != "PENDING":
            return Response({"code": 1, "msg": "该预算没有待审批的调整"}, status=status.HTTP_400_BAD_REQUEST)
        reason = request.data.get("reason", "")
        b.approve_status = "REJECTED"
        b.pending_budget = None
        b.reviewer = request.user
        b.reviewed_at = timezone.now()
        b.reject_reason = reason
        b.save(update_fields=["approve_status", "pending_budget", "reviewer", "reviewed_at", "reject_reason"])
        from apps.common.services import log_action, notify_user
        log_action(request, "REJECT", module="渠道预算", obj=b, detail=f"驳回理由: {reason or '未填写'}")
        if b.created_by:
            notify_user(b.created_by, "预算调整被驳回",
                        f"{b.month} {b.platform.name} 预算调整被驳回。理由：{reason or '未填写'}",
                        category="APPROVAL", link="/ops/budgets")
        return Response({"code": 0, "msg": "已驳回"})

    @action(detail=False, methods=["post"], url_path="batch-set")
    def batch_set(self, request):
        """批量设置预算：month + items 数组（platform、budget、lead_target、deal_target）"""
        month = request.data.get("month")
        items = request.data.get("items") or request.data.get("budgets") or []
        if not month or not items:
            return Response({"code": 1, "msg": "参数 month 和 items 必填"},
                            status=status.HTTP_400_BAD_REQUEST)
        created = updated = skipped = 0
        for item in items:
            platform = resolve_platform(item.get("platform") or item.get("platform_id"))
            if not platform:
                skipped += 1
                continue
            _, is_new = ChannelBudget.objects.update_or_create(
                month=month, platform=platform,
                defaults={
                    "budget": item.get("budget", 0),
                    "lead_target": to_int(item.get("lead_target")),
                    "deal_target": to_int(item.get("deal_target")),
                    "remark": item.get("remark", ""),
                },
            )
            if is_new:
                created += 1
            else:
                updated += 1
        return Response({"code": 0, "msg": "ok",
                         "data": {"month": month, "created": created,
                                  "updated": updated, "skipped": skipped}})


# ---------------- 运营日报 ----------------
class OpsDailyReportViewSet(BizScopeModelViewSet):
    """运营日报"""
    queryset = OpsDailyReport.objects.filter(is_deleted=False)
    serializer_class = OpsDailyReportSerializer
    owner_field = "user"
    ordering_fields = ["date", "total_cost"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = apply_filters(qs, self.request, {"user": "user_id", "date": "date"})
        start = parse_date(self.request.query_params.get("start_date"))
        end = parse_date(self.request.query_params.get("end_date"))
        if start:
            qs = qs.filter(date__gte=start)
        if end:
            qs = qs.filter(date__lte=end)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, created_by=self.request.user)

    @action(detail=False, methods=["post"], url_path="save-or-update")
    def save_or_update(self, request):
        """按用户 + 日期 upsert 日报"""
        report_date = parse_date(request.data.get("date"))
        if not report_date:
            return Response({"code": 1, "msg": "参数 date 必填"},
                            status=status.HTTP_400_BAD_REQUEST)
        user_id = request.data.get("user_id") or request.user.id
        defaults = {
            "total_cost": request.data.get("total_cost", 0),
            "total_lead": to_int(request.data.get("total_lead")),
            "total_wechat": to_int(request.data.get("total_wechat")),
            "total_deal": to_int(request.data.get("total_deal")),
            "highlights": request.data.get("highlights", ""),
            "problems": request.data.get("problems", ""),
            "tomorrow_plan": request.data.get("tomorrow_plan", ""),
            "attachments": request.data.get("attachments", []),
        }
        report, is_new = OpsDailyReport.objects.update_or_create(
            user_id=user_id, date=report_date, defaults=defaults
        )
        return Response({"code": 0, "msg": "ok", "data": {
            "created": is_new,
            "report": OpsDailyReportSerializer(report).data,
        }})

    @action(detail=False, methods=["get"])
    def my(self, request):
        """我的日报"""
        qs = self.get_queryset().filter(user=request.user)
        return paginate(self, qs, OpsDailyReportSerializer)


# ============== 主播板块：获客日报 / 留资台账 / 直播投流 ==============
from .models import AnchorDailyReport, LeadLedger, AnchorAdStat


class AnchorDailyReportViewSet(ScopeModelViewSet):
    """主播获客日报（五大板块）"""
    queryset = AnchorDailyReport.objects.filter(is_deleted=False)
    serializer_class = AnchorDailyReportSerializer
    owner_field = "operator"
    scope_by_department = True
    ordering_fields = ["date", "cost", "lead_count"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = apply_filters(qs, self.request, {
            "channel_type": "channel_type",
            "operator": "operator_id",
        })
        start = parse_date(self.request.query_params.get("start_date"))
        end = parse_date(self.request.query_params.get("end_date"))
        if start:
            qs = qs.filter(date__gte=start)
        if end:
            qs = qs.filter(date__lte=end)
        return qs

    def perform_create(self, serializer):
        serializer.save(operator=self.request.user)

    def perform_update(self, serializer):
        serializer.save(operator=self.request.user)

    @action(detail=False, methods=["post"], url_path="save-or-update")
    def save_or_update(self, request):
        """按 板块+日期+录入人+主播 去重 upsert（每日每板块一条）"""
        report_date = parse_date(request.data.get("date"))
        if not report_date:
            return Response({"code": 1, "msg": "参数 date 必填"}, status=status.HTTP_400_BAD_REQUEST)
        defaults = {
            "anchor_name": request.data.get("anchor_name", ""),
            "cost": request.data.get("cost", 0),
            "lead_count": to_int(request.data.get("lead_count")),
            "valid_lead": to_int(request.data.get("valid_lead")),
            "acquisition_cost": request.data.get("acquisition_cost", 0),
            "account_setup": request.data.get("account_setup", ""),
            "product_content": request.data.get("product_content", ""),
            "exposure": to_int(request.data.get("exposure")),
            "enter_room": to_int(request.data.get("enter_room")),
            "avg_online": request.data.get("avg_online", 0),
            "avg_stay": request.data.get("avg_stay", 0),
            "live_duration": request.data.get("live_duration", 0),
            "live_cost": request.data.get("live_cost", 0),
            "live_lead": to_int(request.data.get("live_lead")),
            "live_valid_lead": to_int(request.data.get("live_valid_lead")),
            "lead_cost": request.data.get("lead_cost", 0),
            "remark": request.data.get("remark", ""),
        }
        obj, is_new = AnchorDailyReport.objects.update_or_create(
            channel_type=request.data.get("channel_type", "PAID"),
            date=report_date,
            operator=request.user,
            anchor_name=request.data.get("anchor_name", ""),
            defaults=defaults,
        )
        return Response({"code": 0, "msg": "ok", "data": {"created": is_new,
                                                          "report": AnchorDailyReportSerializer(obj).data}})

    @action(detail=False, methods=["get"], url_path="daily-summary")
    def daily_summary(self, request):
        """今日总留资汇总：按渠道区分，绑定主播/跟进人，沿用权限隔离（员工自己/主管本部门/老板全部）"""
        date_str = request.query_params.get("date") or timezone.localdate().strftime("%Y-%m-%d")
        target = parse_date(date_str)
        if not target:
            return Response({"code": 1, "msg": "date 格式错误"}, status=status.HTTP_400_BAD_REQUEST)
        qs = self.get_queryset().filter(date=target)
        user = request.user
        led_qs = LeadLedger.objects.filter(is_deleted=False, date=target)
        if not is_big_boss(user):
            led_qs = led_qs.filter(operator__in=list(visible_user_ids(user)))

        def block(ct):
            rows = qs.filter(channel_type=ct)
            return {
                "cost": to_float(rows.aggregate(Sum("cost"))["cost__sum"]),
                "lead_count": rows.aggregate(Sum("lead_count"))["lead_count__sum"] or 0,
                "valid_lead": rows.aggregate(Sum("valid_lead"))["valid_lead__sum"] or 0,
                "live_lead": rows.aggregate(Sum("live_lead"))["live_lead__sum"] or 0,
                "live_valid_lead": rows.aggregate(Sum("live_valid_lead"))["live_valid_lead__sum"] or 0,
            }

        ledger_total = led_qs.count()
        ledger_by_channel = {}
        for ch, _ in LeadLedger.CHANNEL:
            ledger_by_channel[ch] = led_qs.filter(channel=ch).count()

        data = {
            "date": date_str,
            "PAID": block("PAID"),
            "LIVE": block("LIVE"),
            "LOCAL_PUSH": block("LOCAL_PUSH"),
            "AI": block("AI"),
            "SOCIAL": block("SOCIAL"),
            "ledger_total": ledger_total,
            "ledger_by_channel": ledger_by_channel,
        }
        return Response({"code": 0, "msg": "ok", "data": data})

    @action(detail=False, methods=["post"], url_path="save-or-update")
    def save_or_update(self, request):
        """新增或更新主播获客日报：按 unique_together
        (channel_type, date, operator, anchor_name) 查找，存在则更新，不存在则创建；
        operator 始终记为当前登录人（权限隔离底层）。前端「每日数据报表」录入弹窗调用。"""
        data = request.data.copy()
        operator = request.user
        channel_type = data.get("channel_type")
        date = data.get("date")
        anchor_name = data.get("anchor_name") or ""
        existing = self.get_queryset().filter(
            channel_type=channel_type, date=date, operator=operator, anchor_name=anchor_name
        ).first()
        if existing:
            serializer = self.get_serializer(existing, data=data)
        else:
            data["operator"] = operator.id
            serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save(operator=operator)
        return Response({"code": 0, "msg": "ok", "data": self.get_serializer(obj).data})

    @action(detail=False, methods=["get"], url_path="performance-summary")
    def performance_summary(self, request):
        """主播获客数据按日期区间汇总，作为业绩统计/业绩核算模块的数据来源。
        权限隔离沿用 get_queryset（员工看自己 / 主管本部门 / 老板全部）。
        支持 start_date / end_date，缺省为当月 —— 对应日报/周报/月报聚合。"""
        start = parse_date(request.query_params.get("start_date"))
        end = parse_date(request.query_params.get("end_date"))
        if not start:
            start = timezone.localdate().replace(day=1)
        if not end:
            end = timezone.localdate()
        user = request.user
        visible = None
        if not is_big_boss(user):
            visible = list(visible_user_ids(user))

        def scope(qs):
            return qs.filter(operator__in=visible) if visible is not None else qs

        # 1) 获客日报聚合（按录入人）
        rep = scope(self.get_queryset().filter(date__gte=start, date__lte=end))
        rep_agg = rep.values("operator").annotate(
            cost=Sum("cost"), lead_count=Sum("lead_count"), valid_lead=Sum("valid_lead"),
            live_lead=Sum("live_lead"), live_valid_lead=Sum("live_valid_lead"),
            live_cost=Sum("live_cost"),
        )
        rep_map = {r["operator"]: r for r in rep_agg}

        # 2) 留资台账条数（按录入人）
        led = scope(LeadLedger.objects.filter(is_deleted=False, date__gte=start, date__lte=end))
        led_map = {r["operator"]: r["cnt"]
                   for r in led.values("operator").annotate(cnt=Count("id"))}

        # 3) 直播投流（短视频 / 直播间）
        ad = scope(AnchorAdStat.objects.filter(is_deleted=False, date__gte=start, date__lte=end))
        ad_map = {}
        for r in ad.values("operator").annotate(cost=Sum("cost"), lead=Sum("lead_count")):
            ad_map[r["operator"]] = {"cost": to_float(r["cost"]), "lead": r["lead"] or 0}

        operator_ids = set(rep_map) | set(led_map) | set(ad_map)
        # display_name 是 User 模型的属性（非 DB 字段），必须用 Python 解析，
        # 不能用 .values("operator__display_name") 做 DB 级联查询。
        name_map = {}
        real_ids = [oid for oid in operator_ids if oid]
        if real_ids:
            for u in get_user_model().objects.filter(id__in=real_ids):
                name_map[u.id] = getattr(u, "display_name", None) or u.username or f"用户{u.id}"
        items = []
        for oid in operator_ids:
            r = rep_map.get(oid, {})
            cost = to_float(r.get("cost"))
            lead = r.get("lead_count") or 0
            valid = r.get("valid_lead") or 0
            live_lead = r.get("live_lead") or 0
            live_valid = r.get("live_valid_lead") or 0
            live_cost = to_float(r.get("live_cost"))
            a = ad_map.get(oid, {"cost": 0, "lead": 0})
            acq = round(cost / lead, 2) if lead else 0
            items.append({
                "operator_id": oid,
                "operator_name": name_map.get(oid) or (f"用户{oid}" if oid else "未分配"),
                "cost": cost,
                "lead_count": lead,
                "valid_lead": valid,
                "acquisition_cost": acq,
                "live_lead": live_lead,
                "live_valid_lead": live_valid,
                "live_cost": live_cost,
                "ad_cost": a["cost"],
                "ad_lead": a["lead"],
                "ledger_count": led_map.get(oid, 0),
            })
        items.sort(key=lambda x: x["operator_name"])
        total = {
            "cost": round(sum(i["cost"] for i in items), 2),
            "lead_count": sum(i["lead_count"] for i in items),
            "valid_lead": sum(i["valid_lead"] for i in items),
            "live_lead": sum(i["live_lead"] for i in items),
            "live_cost": round(sum(i["live_cost"] for i in items), 2),
            "ad_cost": round(sum(i["ad_cost"] for i in items), 2),
            "ad_lead": sum(i["ad_lead"] for i in items),
            "ledger_count": sum(i["ledger_count"] for i in items),
        }
        return Response({"code": 0, "msg": "ok", "data": {
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d"),
            "items": items,
            "total": total,
        }})


class LeadLedgerViewSet(ScopeModelViewSet):
    """客户留资明细台账"""
    queryset = LeadLedger.objects.filter(is_deleted=False)
    serializer_class = LeadLedgerSerializer
    owner_field = "operator"
    scope_by_department = True
    ordering_fields = ["date", "customer_name"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = apply_filters(qs, self.request, {
            "channel": "channel",
            "follower": "follower_id",
            "is_passed": "is_passed",
        })
        start = parse_date(self.request.query_params.get("start_date"))
        end = parse_date(self.request.query_params.get("end_date"))
        if start:
            qs = qs.filter(date__gte=start)
        if end:
            qs = qs.filter(date__lte=end)
        return qs

    def perform_create(self, serializer):
        serializer.save(operator=self.request.user)

    def perform_update(self, serializer):
        serializer.save(operator=self.request.user)


class AnchorAdStatViewSet(ScopeModelViewSet):
    """直播投流数据（短视频图文 / 直播间 两套）"""
    queryset = AnchorAdStat.objects.filter(is_deleted=False)
    serializer_class = AnchorAdStatSerializer
    owner_field = "operator"
    scope_by_department = True
    ordering_fields = ["date", "cost", "lead_count"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = apply_filters(qs, self.request, {
            "ad_type": "ad_type",
            "platform": "platform",
            "operator": "operator_id",
        })
        start = parse_date(self.request.query_params.get("start_date"))
        end = parse_date(self.request.query_params.get("end_date"))
        if start:
            qs = qs.filter(date__gte=start)
        if end:
            qs = qs.filter(date__lte=end)
        return qs

    def perform_create(self, serializer):
        serializer.save(operator=self.request.user)

    def perform_update(self, serializer):
        serializer.save(operator=self.request.user)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """按日期聚合：短视频图文投流 vs 直播间投流，含环比涨跌"""
        date_str = request.query_params.get("date") or timezone.localdate().strftime("%Y-%m-%d")
        target = parse_date(date_str)
        if not target:
            return Response({"code": 1, "msg": "date 格式错误"}, status=status.HTTP_400_BAD_REQUEST)
        prev = target - timedelta(days=1)
        rows = self.get_queryset().filter(date=target)
        prev_rows = self.get_queryset().filter(date=prev)

        def agg(qs):
            r = qs.aggregate(
                cost=Sum("cost"), impression=Sum("impression"),
                click=Sum("click"), private_msg=Sum("private_msg"),
                lead_count=Sum("lead_count"),
            )
            cost = to_float(r["cost"]); lead = to_int(r["lead_count"])
            return {
                "cost": cost, "impression": to_int(r["impression"]),
                "click": to_int(r["click"]), "private_msg": to_int(r["private_msg"]),
                "lead_count": lead,
                "lead_cost": div(cost, lead),
                "click_rate": to_rate(to_int(r["click"]), to_int(r["impression"])),
            }

        cur = {"SHORT_VIDEO": agg(rows.filter(ad_type="SHORT_VIDEO")),
               "LIVE_ROOM": agg(rows.filter(ad_type="LIVE_ROOM"))}
        pre = {"SHORT_VIDEO": agg(prev_rows.filter(ad_type="SHORT_VIDEO")),
               "LIVE_ROOM": agg(prev_rows.filter(ad_type="LIVE_ROOM"))}

        def ratio(cur_v, pre_v):
            if not pre_v:
                return None
            return round((cur_v - pre_v) / pre_v * 100, 1)

        for k in ("SHORT_VIDEO", "LIVE_ROOM"):
            for m in ("cost", "impression", "click", "private_msg", "lead_count"):
                cur[k][f"{m}_rate"] = ratio(cur[k][m], pre[k][m])
        return Response({"code": 0, "msg": "ok", "data": {"date": date_str,
                                                          "current": cur, "previous": pre}})


class CostRecordViewSet(BizScopeModelViewSet):
    """运营成本记录（2026-11-02 Boss 指示）

    数据口径：管理层（MANAGER）/老板（BOSS/超管）看全公司；员工仅看自己录入的。
    """
    queryset = CostRecord.objects.filter(is_deleted=False)
    serializer_class = CostRecordSerializer
    owner_field = "created_by"
    scope_by_department = False
    log_module = "运营成本录入"
    ordering_fields = ["date", "amount", "created_at"]
    date_field = "date"
    search_fields = ["name", "remark"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(created_by=self.request.user)
