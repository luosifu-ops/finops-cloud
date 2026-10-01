"""运营部：视图集"""
import calendar
from datetime import date, datetime, timedelta

from django.db.models import Q, Count, Sum
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.permissions import visible_user_ids
from apps.common.viewsets import ScopeModelViewSet
from .models import (
    AdPlatform, AdAccount, AdCampaign, AdDailyStat, AdCreative,
    ContentPost, ContentStat, ChannelBudget, OpsDailyReport,
)
from .serializers import (
    AdPlatformSerializer, AdAccountSerializer, AdCampaignSerializer,
    AdDailyStatSerializer, AdCreativeSerializer, ContentPostSerializer,
    ContentStatSerializer, ChannelBudgetSerializer, OpsDailyReportSerializer,
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
    """老板/人事/超管：看全部数据"""
    return user.is_superuser or user.role in ("BOSS", "HR")


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
class AdAccountViewSet(viewsets.ModelViewSet):
    """广告账户"""
    queryset = AdAccount.objects.filter(is_deleted=False)
    serializer_class = AdAccountSerializer
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
class AdCampaignViewSet(viewsets.ModelViewSet):
    """推广计划"""
    queryset = AdCampaign.objects.filter(is_deleted=False)
    serializer_class = AdCampaignSerializer
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
class AdDailyStatViewSet(ScopeModelViewSet):
    """每日投放数据（核心）"""
    queryset = AdDailyStat.objects.all()
    serializer_class = AdDailyStatSerializer
    owner_field = "operator"
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
                "impression": to_int(item.get("impression")),
                "click": to_int(item.get("click")),
                "lead_count": to_int(item.get("lead_count")),
                "valid_lead": to_int(item.get("valid_lead")),
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
class ContentPostViewSet(viewsets.ModelViewSet):
    """内容作品"""
    queryset = ContentPost.objects.filter(is_deleted=False)
    serializer_class = ContentPostSerializer
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
class ContentStatViewSet(viewsets.ModelViewSet):
    """内容数据"""
    queryset = ContentStat.objects.all()
    serializer_class = ContentStatSerializer
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
class ChannelBudgetViewSet(viewsets.ModelViewSet):
    """渠道预算"""
    queryset = ChannelBudget.objects.filter(is_deleted=False)
    serializer_class = ChannelBudgetSerializer
    ordering_fields = ["month", "budget"]

    def get_queryset(self):
        qs = super().get_queryset()
        return apply_filters(qs, self.request, {
            "month": "month",
            "platform": "platform_id",
        })

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

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
class OpsDailyReportViewSet(ScopeModelViewSet):
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
