"""会计部：视图集"""
from datetime import date, datetime, timedelta

from django.db.models import Q, Count
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import User
from apps.common.permissions import visible_user_ids, IsManagerOrAbove
from apps.common.viewsets import ScopeModelViewSet
from .models import (
    TaxType, AccountingClient, MonthlyTask, TaskStep, Voucher, Invoice,
    BankStatement, TaxDeclaration, SocialInsurance, AnnualReport,
    BusinessItem, ClientDocument, HandoverRecord,
)
from .serializers import (
    TaxTypeSerializer, AccountingClientSerializer, MonthlyTaskSerializer,
    TaskStepSerializer, VoucherSerializer, InvoiceSerializer,
    BankStatementSerializer, TaxDeclarationSerializer, SocialInsuranceSerializer,
    AnnualReportSerializer, BusinessItemSerializer, ClientDocumentSerializer,
    HandoverRecordSerializer,
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


def to_int(value, default=0):
    """字符串转整数"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def to_rate(numerator, denominator):
    """完成率(%)，分母为 0 时返回 0"""
    denominator = denominator or 0
    if not denominator:
        return 0
    return round(numerator / denominator * 100, 1)


def is_big_boss(user):
    """老板/人事/超管：看全部数据"""
    return user.is_superuser or user.role in ("BOSS", "HR")


def period_deadline(period):
    """根据所属期间推算申报截止日（次月 15 日）"""
    try:
        year, mon = int(period[:4]), int(period[5:7])
    except (ValueError, IndexError):
        return None
    if mon == 12:
        year, mon = year + 1, 1
    else:
        mon += 1
    return date(year, mon, 15)


def paginate(view, qs, serializer_class):
    """额外 action 的统一分页输出"""
    page = view.paginate_queryset(qs)
    if page is not None:
        return view.get_paginated_response(serializer_class(page, many=True).data)
    return Response({"code": 0, "msg": "ok", "data": serializer_class(qs, many=True).data})


# ---------------- 税种 ----------------
class TaxTypeViewSet(viewsets.ModelViewSet):
    """税种与申报周期"""
    queryset = TaxType.objects.filter(is_deleted=False)
    serializer_class = TaxTypeSerializer
    search_fields = ["name"]
    ordering_fields = ["id", "name"]

    def get_queryset(self):
        qs = super().get_queryset()
        return apply_filters(qs, self.request, {
            "cycle": "cycle",
            "is_active": "is_active",
        })

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# ---------------- 代账客户 ----------------
class AccountingClientViewSet(viewsets.ModelViewSet):
    """代账客户"""
    queryset = AccountingClient.objects.filter(is_deleted=False)
    serializer_class = AccountingClientSerializer
    search_fields = ["customer__name", "tax_no", "tax_bureau"]
    ordering_fields = ["created_at", "service_end"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = apply_filters(qs, self.request, {
            "status": "status",
            "accountant": "accountant_id",
            "assistant": "assistant_id",
            "taxpayer_type": "taxpayer_type",
        })
        user = self.request.user
        if not is_big_boss(user):
            ids = list(visible_user_ids(user))
            qs = qs.filter(Q(accountant__in=ids) | Q(assistant__in=ids))
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["get"])
    def my(self, request):
        """我负责的客户（主办或助理）"""
        qs = self.get_queryset().filter(
            Q(accountant=request.user) | Q(assistant=request.user)
        ).distinct()
        return paginate(self, qs, AccountingClientSerializer)

    @action(detail=False, methods=["get"])
    def expiring(self, request):
        """服务到期预警"""
        days = to_int(request.query_params.get("days"), 60)
        today = timezone.localdate()
        end = today + timedelta(days=days)
        qs = self.get_queryset().filter(
            service_end__isnull=False, service_end__gte=today, service_end__lte=end
        ).order_by("service_end")
        return paginate(self, qs, AccountingClientSerializer)

    @action(detail=False, methods=["get"])
    def overview(self, request):
        """会计部总览：客户总数、类型分布、状态分布、本月做账完成率"""
        qs = self.get_queryset()
        period = request.query_params.get("period") or timezone.localdate().strftime("%Y-%m")
        taxpayer_rows = qs.values("taxpayer_type").annotate(count=Count("id"))
        status_rows = qs.values("status").annotate(count=Count("id"))
        tasks = MonthlyTask.objects.filter(is_deleted=False, period=period,
                                           client_id__in=qs.values("id"))
        task_total = tasks.count()
        task_done = tasks.filter(status__in=["DECLARED", "DONE"]).count()
        return Response({"code": 0, "msg": "ok", "data": {
            "client_total": qs.count(),
            "by_taxpayer_type": [{
                "key": row["taxpayer_type"],
                "name": dict(AccountingClient.TAX_TYPE).get(row["taxpayer_type"], row["taxpayer_type"]),
                "count": row["count"],
            } for row in taxpayer_rows],
            "by_status": [{
                "key": row["status"],
                "name": dict(AccountingClient.STATUS).get(row["status"], row["status"]),
                "count": row["count"],
            } for row in status_rows],
            "period": period,
            "task_total": task_total,
            "task_done": task_done,
            "task_done_rate": to_rate(task_done, task_total),
        }})


# ---------------- 月度做账任务 ----------------
class MonthlyTaskViewSet(ScopeModelViewSet):
    """月度做账任务"""
    queryset = MonthlyTask.objects.filter(is_deleted=False)
    serializer_class = MonthlyTaskSerializer
    owner_field = "accountant"
    ordering_fields = ["period", "deadline", "status"]
    search_fields = ["client__customer__name", "period"]

    def get_queryset(self):
        qs = super().get_queryset()
        return apply_filters(qs, self.request, {
            "period": "period",
            "status": "status",
            "accountant": "accountant_id",
            "client": "client_id",
        })

    def perform_create(self, serializer):
        data = serializer.validated_data
        if data.get("accountant") is None and self.request.user.role == "EMPLOYEE":
            serializer.save(accountant=self.request.user, created_by=self.request.user)
        else:
            serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["post"], url_path="batch-create",
            permission_classes=[IsManagerOrAbove])
    def batch_create(self, request):
        """按期间批量生成做账任务（已存在的跳过）"""
        period = request.query_params.get("period") or request.data.get("period")
        if not period:
            return Response({"code": 1, "msg": "参数 period 必填"},
                            status=status.HTTP_400_BAD_REQUEST)
        deadline = period_deadline(period)
        clients = AccountingClient.objects.filter(is_deleted=False, status="ACTIVE")
        user = request.user
        if not is_big_boss(user):
            ids = list(visible_user_ids(user))
            clients = clients.filter(Q(accountant__in=ids) | Q(assistant__in=ids))
        created = skipped = 0
        for client in clients:
            task, is_new = MonthlyTask.objects.get_or_create(
                client=client, period=period,
                defaults={
                    "accountant": client.accountant,
                    "deadline": deadline,
                    "zero_declare": client.zero_declare,
                    "created_by": request.user,
                },
            )
            if is_new:
                created += 1
            else:
                skipped += 1
        return Response({"code": 0, "msg": "ok",
                         "data": {"period": period, "created": created, "skipped": skipped}})

    @action(detail=True, methods=["post"])
    def advance(self, request, pk=None):
        """推进做账节点：step + status"""
        task = self.get_object()
        step = request.data.get("step")
        step_status = request.data.get("status") or "DONE"
        if not step:
            return Response({"code": 1, "msg": "参数 step 必填"},
                            status=status.HTTP_400_BAD_REQUEST)
        defaults = {"status": step_status, "operator": request.user}
        if step_status == "DONE":
            defaults["finished_at"] = timezone.now()
        else:
            defaults["finished_at"] = None
        task_step, _ = TaskStep.objects.update_or_create(
            task=task, step=step, defaults=defaults
        )
        update_fields = []
        if step == "DECLARE" and step_status == "DONE":
            task.declared_at = timezone.localdate()
            task.status = "DECLARED"
            update_fields.extend(["declared_at", "status"])
        elif step == "VOUCHER" and step_status == "DONE":
            task.voucher_done_at = timezone.localdate()
            update_fields.append("voucher_done_at")
        elif step == "COLLECT" and step_status == "DONE":
            task.doc_received_at = timezone.localdate()
            update_fields.append("doc_received_at")
        if update_fields:
            task.save(update_fields=update_fields)
        return Response({"code": 0, "msg": "ok", "data": {
            "step": TaskStepSerializer(task_step).data,
            "task": MonthlyTaskSerializer(task).data,
        }})

    @action(detail=False, methods=["get"])
    def board(self, request):
        """做账看板：按状态分组数量 + 逾期任务"""
        period = request.query_params.get("period") or timezone.localdate().strftime("%Y-%m")
        qs = self.get_queryset().filter(period=period)
        today = timezone.localdate()
        status_rows = qs.values("status").annotate(count=Count("id"))
        groups = [{
            "status": row["status"],
            "status_name": dict(MonthlyTask.STATUS).get(row["status"], row["status"]),
            "count": row["count"],
        } for row in status_rows]
        overdue = qs.filter(deadline__lt=today).exclude(status__in=["DECLARED", "DONE"])
        return Response({"code": 0, "msg": "ok", "data": {
            "period": period,
            "total": qs.count(),
            "groups": groups,
            "overdue_count": overdue.count(),
            "overdue": MonthlyTaskSerializer(overdue.order_by("deadline")[:50], many=True).data,
        }})

    @action(detail=False, methods=["get"], url_path="my-tasks")
    def my_tasks(self, request):
        """我的做账任务"""
        qs = self.get_queryset().filter(accountant=request.user)
        period = request.query_params.get("period")
        if period:
            qs = qs.filter(period=period)
        return paginate(self, qs, MonthlyTaskSerializer)

    @action(detail=False, methods=["get"])
    def progress(self, request):
        """各会计的任务完成情况"""
        period = request.query_params.get("period")
        qs = self.get_queryset()
        if period:
            qs = qs.filter(period=period)
        rows = qs.values("accountant_id").annotate(total=Count("id"))
        users = {u.id: u for u in User.objects.filter(
            id__in=[r["accountant_id"] for r in rows if r["accountant_id"]])}
        done_rows = qs.filter(status__in=["DECLARED", "DONE"]).values(
            "accountant_id").annotate(done=Count("id"))
        done_map = {r["accountant_id"]: r["done"] for r in done_rows}
        data = []
        for row in rows:
            accountant_id = row["accountant_id"]
            user = users.get(accountant_id)
            done = done_map.get(accountant_id, 0)
            data.append({
                "accountant_id": accountant_id,
                "name": user.display_name if user else "未分配",
                "total": row["total"],
                "done": done,
                "rate": to_rate(done, row["total"]),
            })
        data.sort(key=lambda x: x["done"], reverse=True)
        return Response({"code": 0, "msg": "ok",
                         "data": {"period": period or "全部", "items": data}})


# ---------------- 做账节点 ----------------
class TaskStepViewSet(viewsets.ModelViewSet):
    """做账节点（只读，可改状态）"""
    queryset = TaskStep.objects.filter(is_deleted=False)
    serializer_class = TaskStepSerializer
    http_method_names = ["get", "patch", "head", "options"]
    ordering_fields = ["id"]

    def get_queryset(self):
        qs = super().get_queryset()
        return apply_filters(qs, self.request, {
            "task": "task_id",
            "step": "step",
            "status": "status",
        })


# ---------------- 记账凭证 ----------------
class VoucherViewSet(viewsets.ModelViewSet):
    """记账凭证"""
    queryset = Voucher.objects.filter(is_deleted=False)
    serializer_class = VoucherSerializer
    search_fields = ["voucher_no", "summary", "subject"]
    ordering_fields = ["voucher_no", "date"]

    def get_queryset(self):
        qs = super().get_queryset()
        return apply_filters(qs, self.request, {"task": "task_id"})

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, made_by=self.request.user)

    @action(detail=False, methods=["post"], url_path="batch-create")
    def batch_create(self, request):
        """批量建凭证：task_id + vouchers 数组"""
        task_id = request.data.get("task_id")
        items = request.data.get("vouchers") or []
        if not task_id or not items:
            return Response({"code": 1, "msg": "参数 task_id 和 vouchers 必填"},
                            status=status.HTTP_400_BAD_REQUEST)
        created = 0
        for item in items:
            Voucher.objects.create(
                task_id=task_id,
                voucher_no=item.get("voucher_no", ""),
                date=parse_date(item.get("date")),
                summary=item.get("summary", ""),
                subject=item.get("subject", ""),
                debit=item.get("debit", 0),
                credit=item.get("credit", 0),
                attachment_count=item.get("attachment_count", 0),
                made_by=request.user,
                created_by=request.user,
            )
            created += 1
        return Response({"code": 0, "msg": "ok", "data": {"created": created}})


# ---------------- 发票 ----------------
class InvoiceViewSet(viewsets.ModelViewSet):
    """发票管理"""
    queryset = Invoice.objects.filter(is_deleted=False)
    serializer_class = InvoiceSerializer
    search_fields = ["number", "code", "seller", "buyer"]
    ordering_fields = ["invoice_date", "total"]

    def get_queryset(self):
        qs = super().get_queryset()
        return apply_filters(qs, self.request, {
            "client": "client_id",
            "task": "task_id",
            "direction": "direction",
            "kind": "kind",
            "status": "status",
        })

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["post"], url_path="batch-import")
    def batch_import(self, request):
        """批量导入发票：client_id + invoices 数组"""
        client_id = request.data.get("client_id")
        items = request.data.get("invoices") or []
        if not client_id or not items:
            return Response({"code": 1, "msg": "参数 client_id 和 invoices 必填"},
                            status=status.HTTP_400_BAD_REQUEST)
        created = 0
        for item in items:
            Invoice.objects.create(
                client_id=client_id,
                task_id=item.get("task_id"),
                direction=item.get("direction", "INPUT"),
                kind=item.get("kind", "GENERAL"),
                code=item.get("code", ""),
                number=item.get("number", ""),
                invoice_date=parse_date(item.get("invoice_date")),
                seller=item.get("seller", ""),
                buyer=item.get("buyer", ""),
                amount_ex_tax=item.get("amount_ex_tax", 0),
                tax=item.get("tax", 0),
                total=item.get("total", 0),
                tax_rate=item.get("tax_rate", 0),
                status=item.get("status", "UNUSED"),
                created_by=request.user,
            )
            created += 1
        return Response({"code": 0, "msg": "ok", "data": {"created": created}})


# ---------------- 银行流水 ----------------
class BankStatementViewSet(viewsets.ModelViewSet):
    """银行流水"""
    queryset = BankStatement.objects.filter(is_deleted=False)
    serializer_class = BankStatementSerializer
    search_fields = ["summary", "counterparty"]
    ordering_fields = ["trans_date", "income", "expense"]

    def get_queryset(self):
        qs = super().get_queryset()
        return apply_filters(qs, self.request, {
            "client": "client_id",
            "task": "task_id",
        })

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# ---------------- 纳税申报 ----------------
class TaxDeclarationViewSet(viewsets.ModelViewSet):
    """纳税申报"""
    queryset = TaxDeclaration.objects.filter(is_deleted=False)
    serializer_class = TaxDeclarationSerializer
    ordering_fields = ["deadline", "amount"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = apply_filters(qs, self.request, {
            "task": "task_id",
            "status": "status",
            "tax_type": "tax_type_id",
        })
        user = self.request.user
        if not is_big_boss(user):
            ids = list(visible_user_ids(user))
            qs = qs.filter(Q(operator__in=ids) | Q(task__accountant__in=ids))
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def declare(self, request, pk=None):
        """标记已申报"""
        declaration = self.get_object()
        declaration.status = "DECLARED"
        declaration.declared_at = timezone.now()
        declaration.operator = request.user
        declaration.save(update_fields=["status", "declared_at", "operator"])
        return Response({"code": 0, "msg": "ok",
                         "data": TaxDeclarationSerializer(declaration).data})

    @action(detail=False, methods=["get"])
    def deadline(self, request):
        """临近申报截止的清单"""
        days = to_int(request.query_params.get("days"), 7)
        today = timezone.localdate()
        end = today + timedelta(days=days)
        qs = self.get_queryset().filter(
            status="PENDING", deadline__isnull=False, deadline__gte=today, deadline__lte=end
        ).order_by("deadline")
        return paginate(self, qs, TaxDeclarationSerializer)


# ---------------- 社保公积金 ----------------
class SocialInsuranceViewSet(viewsets.ModelViewSet):
    """社保公积金"""
    queryset = SocialInsurance.objects.filter(is_deleted=False)
    serializer_class = SocialInsuranceSerializer
    ordering_fields = ["month", "total"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = apply_filters(qs, self.request, {
            "client": "client_id",
            "month": "month",
        })
        user = self.request.user
        if not is_big_boss(user):
            ids = list(visible_user_ids(user))
            qs = qs.filter(Q(client__accountant__in=ids) | Q(client__assistant__in=ids))
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# ---------------- 工商年报 ----------------
class AnnualReportViewSet(viewsets.ModelViewSet):
    """工商年报"""
    queryset = AnnualReport.objects.filter(is_deleted=False)
    serializer_class = AnnualReportSerializer
    ordering_fields = ["year", "deadline"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = apply_filters(qs, self.request, {
            "client": "client_id",
            "year": "year",
        })
        user = self.request.user
        if not is_big_boss(user):
            ids = list(visible_user_ids(user))
            qs = qs.filter(Q(client__accountant__in=ids) | Q(client__assistant__in=ids))
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["get"])
    def pending(self, request):
        """未报送清单"""
        year = to_int(request.query_params.get("year"), timezone.localdate().year)
        qs = self.get_queryset().filter(year=year, submitted=False).order_by("deadline")
        return paginate(self, qs, AnnualReportSerializer)


# ---------------- 工商事项 ----------------
class BusinessItemViewSet(viewsets.ModelViewSet):
    """工商事项"""
    queryset = BusinessItem.objects.filter(is_deleted=False)
    serializer_class = BusinessItemSerializer
    search_fields = ["title", "result"]
    ordering_fields = ["created_at", "due_at", "progress"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = apply_filters(qs, self.request, {
            "client": "client_id",
            "item_type": "item_type",
            "status": "status",
            "handler": "handler_id",
        })
        user = self.request.user
        if not is_big_boss(user):
            ids = list(visible_user_ids(user))
            qs = qs.filter(Q(handler__in=ids) | Q(client__accountant__in=ids))
        return qs

    def perform_create(self, serializer):
        data = serializer.validated_data
        if data.get("handler") is None and self.request.user.role == "EMPLOYEE":
            serializer.save(handler=self.request.user, created_by=self.request.user)
        else:
            serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def finish(self, request, pk=None):
        """办结：写完成时间、进度 100、状态 DONE"""
        item = self.get_object()
        item.status = "DONE"
        item.progress = 100
        item.finished_at = timezone.localdate()
        if request.data.get("result"):
            item.result = request.data.get("result")
        item.save(update_fields=["status", "progress", "finished_at", "result"])
        return Response({"code": 0, "msg": "ok", "data": BusinessItemSerializer(item).data})

    @action(detail=False, methods=["get"])
    def my(self, request):
        """我经办的工商事项"""
        qs = self.get_queryset().filter(handler=request.user)
        return paginate(self, qs, BusinessItemSerializer)


# ---------------- 客户资料 ----------------
class ClientDocumentViewSet(viewsets.ModelViewSet):
    """客户资料 / 证件"""
    queryset = ClientDocument.objects.filter(is_deleted=False)
    serializer_class = ClientDocumentSerializer
    search_fields = ["name", "version"]
    ordering_fields = ["expire_at", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = apply_filters(qs, self.request, {
            "client": "client_id",
            "kind": "kind",
        })
        user = self.request.user
        if not is_big_boss(user):
            ids = list(visible_user_ids(user))
            qs = qs.filter(Q(client__accountant__in=ids) | Q(client__assistant__in=ids))
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["get"])
    def expiring(self, request):
        """证件到期预警"""
        days = to_int(request.query_params.get("days"), 30)
        today = timezone.localdate()
        end = today + timedelta(days=days)
        qs = self.get_queryset().filter(
            expire_at__isnull=False, expire_at__gte=today, expire_at__lte=end
        ).order_by("expire_at")
        return paginate(self, qs, ClientDocumentSerializer)


# ---------------- 交接记录 ----------------
class HandoverRecordViewSet(viewsets.ModelViewSet):
    """客户交接记录"""
    queryset = HandoverRecord.objects.filter(is_deleted=False)
    serializer_class = HandoverRecordSerializer
    ordering_fields = ["created_at", "confirmed"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = apply_filters(qs, self.request, {"client": "client_id"})
        user = self.request.user
        if not is_big_boss(user):
            ids = list(visible_user_ids(user))
            qs = qs.filter(Q(from_user__in=ids) | Q(to_user__in=ids))
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        """接收人确认"""
        record = self.get_object()
        if record.confirmed:
            return Response({"code": 1, "msg": "该交接记录已确认"})
        record.confirmed = True
        record.confirmed_at = timezone.now()
        record.checklist = request.data.get("checklist", record.checklist)
        record.save(update_fields=["confirmed", "confirmed_at", "checklist"])
        # 确认后把客户主办会计切换为接收人
        if record.to_user_id and record.client_id:
            AccountingClient.objects.filter(id=record.client_id).update(
                accountant_id=record.to_user_id)
        return Response({"code": 0, "msg": "ok", "data": HandoverRecordSerializer(record).data})
