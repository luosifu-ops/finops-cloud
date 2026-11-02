"""电销部：视图集"""
import calendar
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.db.models import Q, Count, Sum
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

from apps.accounts.models import User
from apps.common.permissions import visible_user_ids, IsManagerOrAbove, IsHR, is_boss
from apps.common.viewsets import ScopeModelViewSet, BizScopeModelViewSet
from .models import (
    Lead, Customer, Contract, CallRecord, FollowUp, SalesTarget, CommissionRule, SalaryRecord,
    Streamer, CustomerTag,
)
from .serializers import (
    LeadSerializer, CustomerSerializer, ContractSerializer, CallRecordSerializer,
    FollowUpSerializer, SalesTargetSerializer, CommissionRuleSerializer, SalaryRecordSerializer,
    StreamerSerializer, CustomerTagSerializer,
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


def to_rate(numerator, denominator):
    """完成率(%)，分母为 0 时返回 0"""
    denominator = float(denominator or 0)
    if not denominator:
        return 0
    return round(float(numerator or 0) / denominator * 100, 1)


def date_filter(qs, request, field, start_key="start_date", end_key="end_date"):
    """按起止日期过滤"""
    start = parse_date(request.query_params.get(start_key))
    end = parse_date(request.query_params.get(end_key))
    if start:
        qs = qs.filter(**{f"{field}__gte": start})
    if end:
        qs = qs.filter(**{f"{field}__lte": end})
    return qs


def is_big_boss(user):
    """老板/超管：看全部经营数据。
    2026-10-29 权限专项：HR 不再自动获得全公司业务数据。"""
    return is_boss(user)


# ---------------- 线索 ----------------
class LeadViewSet(BizScopeModelViewSet):
    """销售线索"""
    queryset = Lead.objects.filter(is_deleted=False)
    serializer_class = LeadSerializer
    owner_field = "owner"
    scope_by_department = True
    log_module = "销售线索"
    search_fields = ["name", "phone", "company"]
    ordering_fields = ["created_at", "assigned_at", "dealt_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        # 未分配的线索对所有人可见（方便主动领取）
        if not is_big_boss(user):
            ids = list(visible_user_ids(user))
            q = Q(owner__in=ids) | Q(owner__isnull=True)
            # 阶段三：主管分配出去的线索，分配人保留可见+可编辑权限
            if hasattr(self.queryset.model, "assigned_by"):
                q = q | Q(assigned_by=user)
            qs = qs.filter(q)
        qs = apply_filters(qs, self.request, {
            "source": "source",
            "status": "status",
            "owner": "owner_id",
            "level": "level",
        })
        return date_filter(qs, self.request, "created_at")

    def perform_create(self, serializer):
        # 2026-10-29：归属人为空时任何角色都回填本人（原来只回填员工，
        # 主管建的数据没有负责人，本部门下属看不到、业绩也统计不到）
        if serializer.validated_data.get("owner") is None:
            serializer.save(owner=self.request.user, created_by=self.request.user)
        else:
            serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["post"], permission_classes=[IsManagerOrAbove])
    def assign(self, request):
        """批量分配线索：ids 数组 + owner_id"""
        ids = request.data.get("ids") or []
        owner_id = request.data.get("owner_id")
        if not ids or not owner_id:
            return Response({"code": 1, "msg": "参数 ids 和 owner_id 必填"},
                            status=status.HTTP_400_BAD_REQUEST)
        owner = User.objects.filter(id=owner_id).first()
        if not owner:
            return Response({"code": 1, "msg": "被分配人不存在"},
                            status=status.HTTP_400_BAD_REQUEST)
        qs = Lead.objects.filter(id__in=ids, is_deleted=False)
        count = qs.update(owner=owner, assigned_by=request.user, status="ASSIGNED", assigned_at=timezone.now())
        # 2026-10-30 增量：线索分配 → 自动发送站内消息通知被分配员工
        from apps.common.services import notify_user
        notify_user(owner, "您有新的线索分配",
                    f"{request.user.display_name or request.user.username} 向您分配了 {count} 条线索，请及时跟进。",
                    category="SYSTEM", link="/sales/followup")
        return Response({"code": 0, "msg": "ok", "data": {"count": count, "owner_id": owner.id}})

    @action(detail=True, methods=["post"])
    def take(self, request, pk=None):
        """领取线索到自己名下"""
        lead = self.get_object()
        if lead.owner_id and lead.owner_id != request.user.id and not is_big_boss(request.user):
            return Response({"code": 1, "msg": "该线索已被他人领取"},
                            status=status.HTTP_400_BAD_REQUEST)
        lead.owner = request.user
        lead.status = "ASSIGNED"
        lead.assigned_at = timezone.now()
        lead.save(update_fields=["owner", "status", "assigned_at"])
        return Response({"code": 0, "msg": "ok", "data": LeadSerializer(lead).data})

    @action(detail=True, methods=["post"])
    def deal(self, request, pk=None):
        """标记成交：可传 amount"""
        lead = self.get_object()
        amount = request.data.get("amount")
        lead.status = "DEAL"
        lead.dealt_at = timezone.now()
        if amount:
            lead.remark = f"{lead.remark}\n成交金额：{amount}".strip()
        lead.save(update_fields=["status", "dealt_at", "remark"])
        return Response({"code": 0, "msg": "ok", "data": LeadSerializer(lead).data})

    @action(detail=True, methods=["post"])
    def lost(self, request, pk=None):
        """标记流失：可传 lost_reason"""
        lead = self.get_object()
        lead.status = "LOST"
        lead.lost_reason = request.data.get("lost_reason", "")
        lead.save(update_fields=["status", "lost_reason"])
        return Response({"code": 0, "msg": "ok", "data": LeadSerializer(lead).data})

    @action(detail=True, methods=["post"], url_path="return-pool")
    def return_pool(self, request, pk=None):
        """退回公海：清空归属人，状态回到待分配（主管/老板或线索归属人可操作）"""
        lead = self.get_object()
        u = request.user
        if not (is_big_boss(u) or lead.owner_id == u.id or getattr(u, "role", "") == "MANAGER"):
            return Response({"code": 1, "msg": "仅主管/老板或线索归属人可退回公海"},
                            status=status.HTTP_403_FORBIDDEN)
        reason = request.data.get("reason", "")
        lead.owner = None
        lead.assigned_by = None
        lead.status = "NEW"
        lead.assigned_at = None
        if reason:
            lead.remark = f"{lead.remark}\n退回公海原因：{reason}".strip()
        lead.save(update_fields=["owner", "assigned_by", "status", "assigned_at", "remark"])
        from apps.common.services import log_action
        log_action(request, "RETURN", module="销售线索", obj=lead, detail=f"退回公海: {reason or '未填写'}")
        return Response({"code": 0, "msg": "ok", "data": LeadSerializer(lead).data})

    @action(detail=True, methods=["get"])
    def timeline(self, request, pk=None):
        """线索穿透详情：基础信息 + 流转时间线（创建/分配/跟进记录/成交/流失）"""
        lead = self.get_object()
        events = []
        if lead.created_at:
            events.append({"time": lead.created_at, "action": "创建", "who": lead.created_by.display_name if lead.created_by_id else "系统", "detail": f"来源 {lead.get_source_display()}，意向 {lead.intention or '未填写'}"})
        if lead.assigned_at:
            who = lead.assigned_by.display_name if lead.assigned_by_id else (lead.owner.display_name if lead.owner_id else "")
            events.append({"time": lead.assigned_at, "action": "分配", "who": who, "detail": f"分配给 {lead.owner.display_name if lead.owner_id else '公海'}"})
        followups = FollowUp.objects.filter(lead=lead, is_deleted=False).order_by("created_at")
        for f in followups:
            events.append({"time": f.created_at, "action": "跟进", "who": f.created_by.display_name if f.created_by_id else "",
                           "detail": f"{f.get_way_display() if hasattr(f, 'get_way_display') else ''} {f.content or ''}".strip()})
        if lead.dealt_at:
            events.append({"time": lead.dealt_at, "action": "成交", "who": lead.owner.display_name if lead.owner_id else "", "detail": lead.remark[:200]})
        if lead.status == "LOST":
            events.append({"time": lead.updated_at, "action": "流失", "who": "", "detail": lead.lost_reason or "未填写原因"})
        events.sort(key=lambda e: e["time"])
        from apps.common.services import log_action
        log_action(request, "OTHER", module="销售线索", obj=lead, detail="查看线索穿透详情")
        data = LeadSerializer(lead).data
        data["timeline"] = [
            {**e, "time": e["time"].strftime("%Y-%m-%d %H:%M")} for e in events
        ]
        return Response({"code": 0, "msg": "ok", "data": data})

    @action(detail=False, methods=["get"])
    def my(self, request):
        """我的线索"""
        qs = self.get_queryset().filter(owner=request.user)
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(LeadSerializer(page, many=True).data)
        return Response({"code": 0, "msg": "ok", "data": LeadSerializer(qs, many=True).data})

    @action(detail=False, methods=["get"], url_path="source-stat")
    def source_stat(self, request):
        """按来源渠道统计线索数、成交量、成交金额、成交率"""
        qs = self.get_queryset()
        rows = qs.values("source").annotate(
            total=Count("id", distinct=True),
            deal_count=Count("id", filter=Q(status="DEAL"), distinct=True),
            deal_amount=Sum("contracts__amount", filter=Q(status="DEAL")),
        )
        data = []
        for row in rows:
            total = row["total"] or 0
            data.append({
                "source": row["source"],
                "source_name": dict(Lead.SOURCE).get(row["source"], row["source"]),
                "total": total,
                "deal_count": row["deal_count"] or 0,
                "deal_amount": to_float(row["deal_amount"]),
                "deal_rate": to_rate(row["deal_count"], total),
            })
        data.sort(key=lambda x: x["total"], reverse=True)
        return Response({"code": 0, "msg": "ok", "data": data})

    @action(detail=False, methods=["get"])
    def funnel(self, request):
        """线索漏斗：总线索→已分配→跟进中→高意向→成交"""
        qs = self.get_queryset()
        total = qs.count()
        stages = [
            ("total", "总线索", total),
            ("assigned", "已分配", qs.filter(status="ASSIGNED").count()),
            ("following", "跟进中", qs.filter(status="FOLLOWING").count()),
            ("intention", "高意向", qs.filter(status="INTENTION").count()),
            ("deal", "已成交", qs.filter(status="DEAL").count()),
        ]
        data = [{"key": key, "name": name, "count": count, "rate": to_rate(count, total)}
                for key, name, count in stages]
        return Response({"code": 0, "msg": "ok", "data": data})


# ---------------- 客户 ----------------
class CustomerViewSet(BizScopeModelViewSet):
    """客户档案"""
    queryset = Customer.objects.filter(is_deleted=False)
    serializer_class = CustomerSerializer
    # 客户归属：业务负责人 / 代账会计
    owner_field = "owner"
    scope_fields = ("owner", "accountant")
    scope_by_department = True
    log_module = "客户档案"
    search_fields = ["name", "phone", "contact", "short_name"]
    ordering_fields = ["created_at", "signed_at", "expire_at"]

    def get_queryset(self):
        # 2026-10-29 修复：原来本方法被重复定义两次，后一个覆盖了前一个，
        # 导致客户档案的数据隔离彻底失效（任何员工都能看到全部客户）。
        # 现合并为单一实现：先走父类范围收窄，再做字段/标签筛选。
        qs = super().get_queryset()
        qs = apply_filters(qs, self.request, {
            "status": "status",
            "owner": "owner_id",
            "accountant": "accountant_id",
            "level": "level",
        })
        # 客户标签筛选（2026-10-29 标签体系）：?tag=<id> 或 ?tag_name=<标签名>
        tag = self.request.query_params.get("tag")
        if tag:
            qs = qs.filter(tags__id=tag).distinct()
        tag_name = self.request.query_params.get("tag_name")
        if tag_name:
            qs = qs.filter(tags__name=tag_name).distinct()
        return qs

    def perform_create(self, serializer):
        # 2026-10-29：归属人为空时任何角色都回填本人（原来只回填员工，
        # 主管建的数据没有负责人，本部门下属看不到、业绩也统计不到）
        if serializer.validated_data.get("owner") is None:
            serializer.save(owner=self.request.user, created_by=self.request.user)
        else:
            serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["get"])
    def my(self, request):
        """我的客户（归属销售或主办会计）"""
        qs = self.get_queryset().filter(
            Q(owner=request.user) | Q(accountant=request.user)
        ).distinct()
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(CustomerSerializer(page, many=True).data)
        return Response({"code": 0, "msg": "ok", "data": CustomerSerializer(qs, many=True).data})

    @action(detail=False, methods=["get"])
    def expiring(self, request):
        """服务到期预警：expire_at 在 N 天内"""
        try:
            days = int(request.query_params.get("days", 30))
        except ValueError:
            days = 30
        today = timezone.localdate()
        end = today + timedelta(days=days)
        qs = self.get_queryset().filter(
            expire_at__isnull=False, expire_at__gte=today, expire_at__lte=end
        ).order_by("expire_at")
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(CustomerSerializer(page, many=True).data)
        return Response({"code": 0, "msg": "ok", "data": CustomerSerializer(qs, many=True).data})


# ---------------- 合同 ----------------
class ContractViewSet(ScopeModelViewSet):
    """合同订单"""
    queryset = Contract.objects.filter(is_deleted=False)
    serializer_class = ContractSerializer
    owner_field = "sales"
    search_fields = ["contract_no", "title", "customer__name"]
    ordering_fields = ["signed_date", "amount", "created_at"]

    def get_queryset(self):
        # 合同职管权限（Boss 2026-09-13 明确）：
        # - 管理人员（BOSS / HR / MANAGER 角色）及运营部(OPS)、管理层(MGMT)部门
        #   -> 可见系统内全部人员创建的所有合同（用于审核/补传/归档）；
        # - 普通账号（EMPLOYEE / LEADER 等）-> 仅可见自己作为签单销售(sales)的合同；
        # - 不改动其他角色在 ScopeModelViewSet 中既有的按归属人隔离逻辑。
        user = self.request.user
        dept_code = getattr(getattr(user, "department", None), "code", None)
        is_manager = bool(
            user.is_authenticated
            and (
                user.is_superuser
                or user.role in ("BOSS", "HR", "MANAGER")
                or dept_code in ("OPS", "MGMT")
            )
        )
        if is_manager:
            # 跳过 ScopeModelViewSet 的「按归属人隔离」，直接取全量
            qs = super(ScopeModelViewSet, self).get_queryset()
        else:
            qs = super().get_queryset()
            # 阶段三：主管分配出去的合同，分配人保留可见+可编辑权限
            # 2026-10-28 修复 500：distinct 查询不可与非 distinct 查询合并，两侧先统一 distinct
            if hasattr(qs.model, "assigned_by"):
                assigned_qs = super(ScopeModelViewSet, self).get_queryset().filter(assigned_by=user).distinct()
                qs = (qs.distinct() | assigned_qs).distinct()
        qs = apply_filters(qs, self.request, {
            "status": "status",
            "biz_type": "biz_type",
            "sales": "sales_id",
            "customer": "customer_id",
        })
        return date_filter(qs, self.request, "signed_date")

    def perform_create(self, serializer):
        data = serializer.validated_data
        if data.get("sales") is None and self.request.user.role == "EMPLOYEE":
            serializer.save(sales=self.request.user, assigned_by=self.request.user, created_by=self.request.user)
        else:
            serializer.save(assigned_by=self.request.user, created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def payment(self, request, pk=None):
        """收款登记：累加 received，收满自动改状态为 PAID"""
        contract = self.get_object()
        try:
            amount = Decimal(str(request.data.get("amount") or 0))
        except (TypeError, ValueError, InvalidOperation):
            return Response({"code": 1, "msg": "金额格式不正确"},
                            status=status.HTTP_400_BAD_REQUEST)
        if amount <= 0:
            return Response({"code": 1, "msg": "收款金额必须大于 0"},
                            status=status.HTTP_400_BAD_REQUEST)
        contract.received = (contract.received or Decimal("0")) + amount
        update_fields = ["received"]
        if contract.received >= (contract.amount or Decimal("0")) and contract.status == "PENDING":
            contract.status = "PAID"
            update_fields.append("status")
        contract.save(update_fields=update_fields)
        return Response({"code": 0, "msg": "ok", "data": ContractSerializer(contract).data})

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def upload_attachment(self, request, pk=None):
        """上传合同扫描件（pdf / 图片 / word 等，单文件 ≤ 20MB）"""
        contract = self.get_object()
        f = request.FILES.get("attachment")
        if not f:
            return Response({"code": 1, "msg": "未接收到文件"}, status=status.HTTP_400_BAD_REQUEST)
        if f.size and f.size > 20 * 1024 * 1024:
            return Response({"code": 1, "msg": "文件不能超过 20MB"}, status=status.HTTP_400_BAD_REQUEST)
        contract.attachment.save(f.name, f, save=True)
        return Response({"code": 0, "msg": "ok",
                         "data": ContractSerializer(contract, context={"request": request}).data})

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def upload_payment_screenshot(self, request, pk=None):
        """上传客户付款截图（图片，单文件 ≤ 20MB）"""
        contract = self.get_object()
        f = request.FILES.get("payment_screenshot")
        if not f:
            return Response({"code": 1, "msg": "未接收到文件"}, status=status.HTTP_400_BAD_REQUEST)
        if f.size and f.size > 20 * 1024 * 1024:
            return Response({"code": 1, "msg": "文件不能超过 20MB"}, status=status.HTTP_400_BAD_REQUEST)
        contract.payment_screenshot.save(f.name, f, save=True)
        return Response({"code": 0, "msg": "ok",
                         "data": ContractSerializer(contract, context={"request": request}).data})

    @action(detail=False, methods=["get"])
    def my(self, request):
        """我的合同"""
        qs = self.get_queryset().filter(sales=request.user)
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(ContractSerializer(page, many=True).data)
        return Response({"code": 0, "msg": "ok", "data": ContractSerializer(qs, many=True).data})

    def _target_amount(self, month, scope, obj_id, user=None):
        """取目标：优先 SalesTarget，其次 User.month_target"""
        lookup = {"month": month, "scope": scope}
        if scope == "PERSON":
            lookup["user_id"] = obj_id
        elif scope == "TEAM":
            lookup["team_id"] = obj_id
        elif scope == "DEPARTMENT":
            lookup["department_id"] = obj_id
        target = SalesTarget.objects.filter(**lookup).order_by("-id").first()
        if target:
            return to_float(target.amount_target)
        if scope == "PERSON" and user is not None:
            return to_float(user.month_target)
        return 0

    @action(detail=False, methods=["get"])
    def performance(self, request):
        """业绩统计：scope=person/team/department，按目标计算完成率"""
        month = request.query_params.get("month")
        scope = (request.query_params.get("scope") or "person").upper()
        start, end = month_range(month)
        month = start.strftime("%Y-%m")
        qs = self.get_queryset().filter(signed_date__gte=start, signed_date__lte=end)

        if scope == "TEAM":
            rows = qs.values("sales__team_id", "sales__team__name").annotate(
                sum_amount=Sum("amount"),
                sum_received=Sum("received"),
                order_count=Count("id"),
            )
            data = [{
                "id": row["sales__team_id"],
                "name": row["sales__team__name"] or "未分组",
                "amount": to_float(row["sum_amount"]),
                "received": to_float(row["sum_received"]),
                "order_count": row["order_count"],
                "target": self._target_amount(month, "TEAM", row["sales__team_id"]),
            } for row in rows]
            scope_key = "TEAM"
        elif scope == "DEPARTMENT":
            rows = qs.values("sales__department_id", "sales__department__name").annotate(
                sum_amount=Sum("amount"),
                sum_received=Sum("received"),
                order_count=Count("id"),
            )
            data = [{
                "id": row["sales__department_id"],
                "name": row["sales__department__name"] or "未分配",
                "amount": to_float(row["sum_amount"]),
                "received": to_float(row["sum_received"]),
                "order_count": row["order_count"],
                "target": self._target_amount(month, "DEPARTMENT", row["sales__department_id"]),
            } for row in rows]
            scope_key = "DEPARTMENT"
        else:
            rows = qs.values("sales_id").annotate(
                sum_amount=Sum("amount"),
                sum_received=Sum("received"),
                order_count=Count("id"),
            )
            users = {u.id: u for u in User.objects.filter(
                id__in=[row["sales_id"] for row in rows if row["sales_id"]])}
            data = []
            for row in rows:
                user = users.get(row["sales_id"])
                data.append({
                    "id": row["sales_id"],
                    "name": user.display_name if user else "未指定",
                    "amount": to_float(row["sum_amount"]),
                    "received": to_float(row["sum_received"]),
                    "order_count": row["order_count"],
                    "target": self._target_amount(month, "PERSON", row["sales_id"], user),
                })
            scope_key = "PERSON"

        for item in data:
            item["rate"] = to_rate(item["amount"], item["target"])
        data.sort(key=lambda x: x["amount"], reverse=True)
        total = {
            "amount": round(sum(i["amount"] for i in data), 2),
            "received": round(sum(i["received"] for i in data), 2),
            "order_count": sum(i["order_count"] for i in data),
            "target": round(sum(i["target"] for i in data), 2),
        }
        total["rate"] = to_rate(total["amount"], total["target"])
        return Response({"code": 0, "msg": "ok", "data": {
            "month": month, "scope": scope_key, "total": total, "items": data,
        }})

    @action(detail=False, methods=["get"])
    def rank(self, request):
        """个人业绩排行榜（降序，含目标与完成率）"""
        month = request.query_params.get("month")
        start, end = month_range(month)
        month = start.strftime("%Y-%m")
        qs = self.get_queryset().filter(signed_date__gte=start, signed_date__lte=end)
        rows = qs.values("sales_id").annotate(
            sum_amount=Sum("amount"),
            sum_received=Sum("received"),
            order_count=Count("id"),
        )
        stat_map = {row["sales_id"]: row for row in rows if row["sales_id"]}
        # 有目标但本月未开单的人也要上榜
        target_user_ids = set(SalesTarget.objects.filter(
            month=month, scope="PERSON").values_list("user_id", flat=True))
        user_ids = set(stat_map.keys()) | {i for i in target_user_ids if i}
        users = User.objects.filter(id__in=user_ids, is_active=True).order_by("department", "id")
        data = []
        for user in users:
            row = stat_map.get(user.id)
            amount = to_float(row["sum_amount"]) if row else 0
            received = to_float(row["sum_received"]) if row else 0
            order_count = row["order_count"] if row else 0
            target = self._target_amount(month, "PERSON", user.id, user)
            data.append({
                "user_id": user.id,
                "name": user.display_name,
                "department_name": user.department.name if user.department_id else "",
                "team_name": user.team.name if user.team_id else "",
                "amount": amount,
                "received": received,
                "order_count": order_count,
                "target": target,
                "rate": to_rate(amount, target),
            })
        data.sort(key=lambda x: (x["amount"], x["order_count"]), reverse=True)
        for index, item in enumerate(data, start=1):
            item["rank"] = index
        return Response({"code": 0, "msg": "ok", "data": {"month": month, "items": data}})


# ---------------- 通话记录 ----------------
class CallRecordViewSet(BizScopeModelViewSet):
    """通话记录"""
    queryset = CallRecord.objects.all()
    serializer_class = CallRecordSerializer
    owner_field = "user"
    scope_by_department = True
    log_module = "通话记录"
    ordering_fields = ["created_at", "duration"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = apply_filters(qs, self.request, {
            "user": "user_id",
            "result": "result",
            "lead": "lead_id",
            "customer": "customer_id",
        })
        return date_filter(qs, self.request, "created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"], url_path="add-wechat")
    def add_wechat(self, request, pk=None):
        """标记已加微"""
        record = self.get_object()
        record.has_wechat = True
        record.save(update_fields=["has_wechat"])
        return Response({"code": 0, "msg": "ok", "data": CallRecordSerializer(record).data})

    @action(detail=False, methods=["get"], url_path="my-stat")
    def my_stat(self, request):
        """我的通话量统计：总量、接通量、加微数、接通率"""
        month = request.query_params.get("month")
        start, end = month_range(month)
        qs = self.get_queryset().filter(user=request.user,
                                        created_at__date__gte=start,
                                        created_at__date__lte=end)
        total = qs.count()
        connected = qs.filter(result="CONNECTED").count()
        wechat = qs.filter(has_wechat=True).count()
        return Response({"code": 0, "msg": "ok", "data": {
            "month": start.strftime("%Y-%m"),
            "total": total,
            "connected": connected,
            "wechat_added": wechat,
            "connect_rate": to_rate(connected, total),
            "duration": qs.aggregate(total_duration=Sum("duration"))["total_duration"] or 0,
        }})


# ---------------- 跟进记录 ----------------
class FollowUpViewSet(BizScopeModelViewSet):
    """跟进记录"""
    queryset = FollowUp.objects.filter(is_deleted=False)
    serializer_class = FollowUpSerializer
    owner_field = "user"
    scope_by_department = True
    log_module = "跟进记录"
    search_fields = ["content", "next_action"]
    ordering_fields = ["created_at", "next_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        return apply_filters(qs, self.request, {
            "lead": "lead_id",
            "customer": "customer_id",
            "user": "user_id",
            "way": "way",
        })

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, created_by=self.request.user)

    @action(detail=False, methods=["get"])
    def upcoming(self, request):
        """今日/明日待跟进"""
        try:
            days = int(request.query_params.get("days", 1))
        except ValueError:
            days = 1
        start = timezone.localtime()
        end = start + timedelta(days=days + 1)
        qs = self.get_queryset().filter(
            next_at__isnull=False, next_at__gte=start, next_at__lte=end
        ).order_by("next_at")
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(FollowUpSerializer(page, many=True).data)
        return Response({"code": 0, "msg": "ok", "data": FollowUpSerializer(qs, many=True).data})


# ---------------- 业绩目标 ----------------
class SalesTargetViewSet(viewsets.ModelViewSet):
    """业绩目标"""
    queryset = SalesTarget.objects.filter(is_deleted=False)
    serializer_class = SalesTargetSerializer
    ordering_fields = ["month", "amount_target"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = apply_filters(qs, self.request, {
            "month": "month",
            "scope": "scope",
            "user": "user_id",
            "team": "team_id",
            "department": "department_id",
        })
        user = self.request.user
        if not is_big_boss(user):
            ids = list(visible_user_ids(user))
            qs = qs.filter(Q(user__in=ids) | Q(user__isnull=True))
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["post"], url_path="batch-set",
            permission_classes=[IsManagerOrAbove])
    def batch_set(self, request):
        """批量设置目标：month + scope + targets 数组"""
        month = request.data.get("month")
        scope = (request.data.get("scope") or "PERSON").upper()
        targets = request.data.get("targets") or []
        if not month or not targets:
            return Response({"code": 1, "msg": "参数 month 和 targets 必填"},
                            status=status.HTTP_400_BAD_REQUEST)
        created = updated = 0
        for item in targets:
            base = {"month": month, "scope": scope}
            if scope == "PERSON":
                base["user_id"] = item.get("user_id")
            elif scope == "TEAM":
                base["team_id"] = item.get("team_id")
            elif scope == "DEPARTMENT":
                base["department_id"] = item.get("department_id")
            defaults = {
                "amount_target": item.get("amount_target", 0),
                "order_target": item.get("order_target", 0),
                "call_target": item.get("call_target", 0),
            }
            _, is_new = SalesTarget.objects.update_or_create(defaults=defaults, **base)
            if is_new:
                created += 1
            else:
                updated += 1
        return Response({"code": 0, "msg": "ok",
                         "data": {"created": created, "updated": updated}})


# ---------------- 提成规则 ----------------
class CommissionRuleViewSet(viewsets.ModelViewSet):
    """提成规则"""
    queryset = CommissionRule.objects.filter(is_deleted=False)
    serializer_class = CommissionRuleSerializer
    search_fields = ["name"]
    ordering_fields = ["effective_month", "id"]

    def get_queryset(self):
        qs = super().get_queryset()
        return apply_filters(qs, self.request, {
            "rule_type": "rule_type",
            "department": "department_id",
            "effective_month": "effective_month",
        })

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# 公司统一提成阶梯（Boss 2026-09-04 定）：底薪 3500（已含全勤，不另发）
# <1万 10% / 1万~1.75万 15% / 1.75万~2.5万 20% / ≥2.5万 25%
COMPANY_LADDER = [
    {"min": 0, "max": 10000, "rate": 10},
    {"min": 10000, "max": 17500, "rate": 15},
    {"min": 17500, "max": 25000, "rate": 20},
    {"min": 25000, "max": 10 ** 12, "rate": 25},
]


def calc_commission(rule, performance):
    """按提成规则计算提成金额。rule: CommissionRule 实例；performance: 业绩(数字)"""
    if not rule:
        return Decimal("0"), ""
    performance = Decimal(str(performance or 0))
    if rule.rule_type == "RATE":
        comm = performance * (rule.rate or 0) / Decimal("100")
    elif rule.rule_type == "FIXED":
        # 固定金额按单：固定按 1 单基准；如需按订单数可前端扩展传 order_count
        comm = rule.fixed_amount or 0
    elif rule.rule_type == "LADDER":
        comm = Decimal("0")
        for t in (rule.ladder or []):
            try:
                tmin = Decimal(str(t.get("min", 0)))
                tmax = Decimal(str(t.get("max", 0)))
                trate = Decimal(str(t.get("rate", 0)))
            except (InvalidOperation, TypeError, ValueError):
                continue
            overlap = min(performance, tmax) - tmin
            if overlap > 0:
                comm += overlap * trate / Decimal("100")
    else:
        comm = Decimal("0")
    return Decimal(str(round(comm, 2))), rule.name


class SalaryViewSet(viewsets.ModelViewSet):
    """工资核算：列表/保存 + 业绩→自动核算"""
    queryset = SalaryRecord.objects.filter(is_deleted=False)
    serializer_class = SalaryRecordSerializer
    search_fields = ["user__username", "user__first_name", "month"]
    ordering_fields = ["month", "total", "performance"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or user.role in ("BOSS", "HR"):
            pass
        elif user.role in ("MANAGER", "LEADER"):
            ids = visible_user_ids(user)
            qs = qs.filter(user_id__in=ids)
        else:
            qs = qs.filter(user=user)
        month = self.request.query_params.get("month")
        if month:
            qs = qs.filter(month=month)
        uid = self.request.query_params.get("user_id")
        if uid:
            qs = qs.filter(user_id=uid)
        return qs

    @action(detail=False, methods=["post"], permission_classes=[IsHR])
    def calc(self, request):
        """输入业绩 → 自动核算工资明细。
        入参: user_id, month, performance, bonus(可选), deduction(可选)"""
        user_id = request.data.get("user_id")
        month = request.data.get("month") or timezone.localdate().strftime("%Y-%m")
        performance = request.data.get("performance") or 0
        bonus = request.data.get("bonus") or 0
        deduction = request.data.get("deduction") or 0
        try:
            user = User.objects.get(id=user_id, is_active=True)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({"code": 1, "msg": "员工不存在"}, status=status.HTTP_400_BAD_REQUEST)

        # 底薪：以员工设置为准；未设置则按公司标准 3500（已含全勤，不另发）
        base_salary = user.base_salary if user.base_salary else Decimal("3500")
        # 公司统一阶梯提成（Boss 2026-09-04 定），不依赖数据库规则
        rule = CommissionRule(rule_type="LADDER", ladder=COMPANY_LADDER, name="公司标准阶梯提成")
        commission, rule_name = calc_commission(rule, performance)
        base_salary = Decimal(str(base_salary))
        bonus = Decimal(str(bonus))
        deduction = Decimal(str(deduction))
        commission = Decimal(str(commission))
        total = base_salary + commission + bonus - deduction

        return Response({
            "code": 0,
            "data": {
                "user_id": user.id,
                "user_name": user.display_name,
                "month": month,
                "base_salary": float(base_salary),
                "performance": float(Decimal(str(performance))),
                "commission": float(commission),
                "commission_rule": rule_name,
                "bonus": float(bonus),
                "deduction": float(deduction),
                "total": float(total),
            },
        })

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    # —— 写入操作仅人事/老板（Boss 2026-09-14 安全加固）——
    # 列表/读取仍按 get_queryset 做角色+部门隔离（员工看自己、经理看本部门、HR/Boss 看全部）；
    # 但新增/修改/删除薪资记录必须有 HR 或 Boss 权限，杜绝普通员工伪造或删除他人薪资。
    def _assert_hr(self):
        if not IsHR().has_permission(self.request, self):
            raise PermissionDenied("仅人事主管或老板可维护薪资数据")

    def create(self, request, *args, **kwargs):
        self._assert_hr()
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        self._assert_hr()
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        self._assert_hr()
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self._assert_hr()
        instance = self.get_object()
        instance.is_deleted = True
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------- 主播 ----------------
class StreamerViewSet(BizScopeModelViewSet):
    """主播（直播获客/带货）：负责人与部门维度做数据隔离"""
    queryset = Streamer.objects.filter(is_deleted=False)
    serializer_class = StreamerSerializer
    owner_field = "manager"
    scope_by_department = True
    log_module = "主播管理"
    search_fields = ["name", "real_name", "account", "phone"]
    ordering_fields = ["created_at", "fans_count", "gmv", "live_count"]

    def get_queryset(self):
        qs = super().get_queryset()
        return apply_filters(qs, self.request, {
            "platform": "platform",
            "status": "status",
            "department": "department_id",
            "manager": "manager_id",
        })

    def perform_create(self, serializer):
        data = serializer.validated_data
        if data.get("manager") is None and self.request.user.role == "EMPLOYEE":
            serializer.save(manager=self.request.user, created_by=self.request.user)
        else:
            serializer.save(created_by=self.request.user)


class CustomerTagViewSet(viewsets.ModelViewSet):
    """客户标签 CRUD（2026-10-29 Boss 专项：客户档案标签分级）

    标签是公司共享字典，不按个人隔离（不继承 ScopeModelViewSet）；支持启用/停用与排序。
    """
    queryset = CustomerTag.objects.filter(is_deleted=False)
    serializer_class = CustomerTagSerializer
    log_module = "客户标签"
    search_fields = ["name"]
    ordering_fields = ["sort", "id"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("active") == "1":
            qs = qs.filter(is_active=True)
        return qs

    def perform_create(self, serializer):
        inst = serializer.save(created_by=self.request.user)
        from apps.common.services import log_action
        log_action(self.request, "CREATE", module="客户标签", obj=inst, detail=f"新建标签 {inst.name}")

    def perform_destroy(self, instance):
        from apps.common.services import log_action
        log_action(self.request, "DELETE", module="客户标签", obj=instance)
        instance.soft_delete()
