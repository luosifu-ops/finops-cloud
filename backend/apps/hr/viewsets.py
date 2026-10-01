"""人事考勤与审批：视图集"""
from datetime import datetime, time as dtime
from decimal import Decimal

from django.db.models import Sum, Count, Q
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.accounts.models import User, Department
from apps.common.permissions import visible_user_ids, IsLeaderOrAbove, IsHR
from apps.common.viewsets import ScopeModelViewSet
from apps.sales.models import (
    SalaryRecord, Contract, Lead, Customer, CallRecord, SalesTarget, CommissionRule,
)
from apps.sales.serializers import SalaryRecordSerializer
from apps.sales.viewsets import calc_commission, COMPANY_LADDER
from .models import (
    AttendanceRule, Attendance, AttendanceStat,
    LeaveApplication, OvertimeApplication, TravelApplication, ExpenseApplication,
    Approval, ApprovalStep,
    JobLevel, ExternalContact, UserAttachment, EmployeeChangeLog, LaborContract,
    RegularizationApplication, TransferApplication, ResignApplication,
    AttendanceGroup, ShiftSchedule, LeaveBalance, PurchaseApplication,
    SealApplication, PerformancePlan, PerformanceReview,
    AddressBookVisibility, RolePreset,
)
from .serializers import (
    AttendanceRuleSerializer, AttendanceSerializer, AttendanceStatSerializer,
    LeaveApplicationSerializer, OvertimeApplicationSerializer,
    TravelApplicationSerializer, ExpenseApplicationSerializer,
    ApprovalSerializer, ApprovalStepSerializer,
    JobLevelSerializer, ExternalContactSerializer, UserAttachmentSerializer,
    EmployeeChangeLogSerializer, LaborContractSerializer,
    RegularizationApplicationSerializer, TransferApplicationSerializer,
    ResignApplicationSerializer, AttendanceGroupSerializer, ShiftScheduleSerializer,
    LeaveBalanceSerializer, PurchaseApplicationSerializer, SealApplicationSerializer,
    PerformancePlanSerializer, PerformanceReviewSerializer,
    AddressBookVisibilitySerializer, RolePresetSerializer,
)

# 可审批申请单的角色
APPROVE_ROLES = ("BOSS", "MANAGER", "HR")
# 可查看全公司数据的角色
ALL_DATA_ROLES = ("BOSS", "HR")


def is_higher(user):
    """是否可查看全公司数据（老板 / 人事 / 超管）"""
    return bool(user and user.is_authenticated and (user.is_superuser or user.role in ALL_DATA_ROLES))


def can_approve(user):
    """是否可审批申请单"""
    return bool(user and user.is_authenticated and (user.is_superuser or user.role in APPROVE_ROLES))


def as_time(value):
    """把 TimeField 的值统一转成 datetime.time（兼容未入库的字符串默认值）"""
    if isinstance(value, dtime):
        return value
    try:
        return datetime.strptime(str(value)[:5], "%H:%M").time()
    except (ValueError, TypeError):
        return None


def get_default_rule():
    """取当前生效的考勤规则"""
    return (AttendanceRule.objects.filter(is_default=True, is_deleted=False).first()
            or AttendanceRule.objects.filter(is_deleted=False).first())


def parse_month(month):
    """解析 2026-09 形式的月份，返回 (年, 月)；解析失败返回 (None, None)"""
    try:
        parts = str(month).split("-")
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError, TypeError, AttributeError):
        return None, None


def calc_days(start, end):
    """按起止时间算天数：不足一天按 0.5 天，超出整天部分按 0.5 天计"""
    if not start or not end:
        return Decimal("0")
    seconds = (end - start).total_seconds()
    if seconds <= 0:
        return Decimal("0")
    days = seconds / 86400
    if days < 1:
        return Decimal("0.5")
    full = int(days)
    return Decimal(full) + (Decimal("0.5") if days - full > 0 else Decimal("0"))


def calc_hours(start, end, digits=1):
    """按起止时间算小时数"""
    if not start or not end:
        return Decimal("0")
    seconds = (end - start).total_seconds()
    if seconds <= 0:
        return Decimal("0")
    return Decimal(str(round(seconds / 3600, digits)))


def ok(data=None, msg="ok"):
    """额外动作的统一返回格式"""
    return Response({"code": 0, "msg": msg, "data": data})


def fail(msg, code=1):
    """额外动作的错误返回"""
    return Response({"code": code, "msg": msg})


class AttendanceRuleViewSet(viewsets.ModelViewSet):
    """考勤规则：全公司共用"""
    queryset = AttendanceRule.objects.filter(is_deleted=False).order_by("-is_default", "id")
    serializer_class = AttendanceRuleSerializer
    search_fields = ["name"]


class AttendanceViewSet(ScopeModelViewSet):
    """考勤记录：支持打卡、我的考勤、团队统计"""
    queryset = Attendance.objects.select_related("user", "user__department").all()
    serializer_class = AttendanceSerializer
    owner_field = "user"
    ordering_fields = ["date", "check_in", "user"]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        user_id = params.get("user")
        if user_id:
            qs = qs.filter(user_id=user_id)
        date = params.get("date")
        if date:
            qs = qs.filter(date=date)
        status_value = params.get("status")
        if status_value:
            qs = qs.filter(status=status_value)
        start_date = params.get("start_date")
        if start_date:
            qs = qs.filter(date__gte=start_date)
        end_date = params.get("end_date")
        if end_date:
            qs = qs.filter(date__lte=end_date)
        # 跨部门查询需要主管及以上权限
        dept_id = params.get("department_id")
        if dept_id:
            user = self.request.user
            if is_higher(user) or str(user.department_id) == str(dept_id):
                qs = qs.filter(user__department_id=dept_id)
            else:
                raise PermissionDenied("无权限查看其他部门考勤")
        return qs

    def perform_create(self, serializer):
        """未指定员工时默认记在当前用户名下"""
        if serializer.validated_data.get("user"):
            serializer.save()
        else:
            serializer.save(user=self.request.user)

    @action(detail=False, methods=["post"], url_path="check-in")
    def check_in(self, request):
        """上班打卡：已有记录则更新打卡时间，并按考勤规则判定迟到"""
        now = timezone.now()
        local = timezone.localtime(now)
        location = request.data.get("location", "")
        att, _ = Attendance.objects.get_or_create(
            user=request.user, date=local.date(), defaults={"check_in": now}
        )
        att.check_in = now
        if location:
            att.check_in_location = location

        late_minutes = 0
        att_status = "NORMAL"
        rule = get_default_rule()
        if rule:
            start = as_time(rule.work_start)
            if start:
                diff = (datetime.combine(local.date(), local.time())
                        - datetime.combine(local.date(), start)).total_seconds() / 60
                if diff > rule.late_minutes:
                    late_minutes = int(diff)
                    att_status = "LATE"
        att.late_minutes = late_minutes
        att.status = att_status
        att.save()
        return ok(AttendanceSerializer(att).data, msg="打卡成功")

    @action(detail=False, methods=["post"], url_path="check-out")
    def check_out(self, request):
        """下班打卡：计算工作时长，早于下班时间记为早退"""
        now = timezone.now()
        local = timezone.localtime(now)
        location = request.data.get("location", "")
        att = Attendance.objects.filter(user=request.user, date=local.date()).first()
        if not att:
            return fail("今天还没有上班打卡，请先打卡")
        att.check_out = now
        if location:
            att.check_out_location = location
        if att.check_in:
            att.work_hours = calc_hours(att.check_in, now, digits=2)
        rule = get_default_rule()
        if rule:
            end = as_time(rule.work_end)
            if end and local.time() < end and att.status in ("NORMAL", "LATE"):
                att.status = "EARLY"
        att.save()
        return ok(AttendanceSerializer(att).data, msg="签退成功")

    @action(detail=False, methods=["get"], url_path="my")
    def my(self, request):
        """我的当月考勤明细"""
        month = request.query_params.get("month") or timezone.localtime(timezone.now()).strftime("%Y-%m")
        qs = self.filter_queryset(self.get_queryset()).filter(user=request.user)
        year, mon = parse_month(month)
        if year and mon:
            qs = qs.filter(date__year=year, date__month=mon)
        return ok(AttendanceSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="today-status")
    def today_status(self, request):
        """今日打卡情况"""
        today = timezone.localtime(timezone.now()).date()
        att = Attendance.objects.filter(user=request.user, date=today).first()
        if not att:
            return ok({"date": today, "checked_in": False, "checked_out": False,
                       "status": "", "status_name": "未打卡"})
        return ok({
            "date": today,
            "checked_in": bool(att.check_in),
            "checked_out": bool(att.check_out),
            "check_in": att.check_in,
            "check_out": att.check_out,
            "status": att.status,
            "status_name": att.get_status_display(),
            "late_minutes": att.late_minutes,
            "work_hours": att.work_hours,
        })

    @action(detail=False, methods=["get"], url_path="team-stat",
            permission_classes=[IsLeaderOrAbove])
    def team_stat(self, request):
        """团队考勤统计：出勤天数 / 迟到 / 早退 / 旷工"""
        month = request.query_params.get("month") or timezone.localtime(timezone.now()).strftime("%Y-%m")
        qs = self.get_queryset()
        year, mon = parse_month(month)
        if year and mon:
            qs = qs.filter(date__year=year, date__month=mon)

        users = {}
        for att in qs.select_related("user"):
            item = users.setdefault(att.user_id, {
                "user": att.user_id,
                "user_name": att.user.display_name,
                "department_name": att.user.department.name if att.user.department else "",
                "days": 0, "late_times": 0, "early_times": 0, "absent_times": 0,
            })
            item["days"] += 1
            if att.status == "LATE":
                item["late_times"] += 1
            elif att.status == "EARLY":
                item["early_times"] += 1
            elif att.status == "ABSENT":
                item["absent_times"] += 1
        return ok({"month": month, "list": list(users.values())})


class AttendanceStatViewSet(viewsets.ReadOnlyModelViewSet):
    """考勤月报（只读）"""
    queryset = AttendanceStat.objects.select_related("user", "user__department").all()
    serializer_class = AttendanceStatSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not is_higher(user):
            qs = qs.filter(user__in=visible_user_ids(user))
        month = self.request.query_params.get("month")
        if month:
            qs = qs.filter(month=month)
        user_id = self.request.query_params.get("user")
        if user_id:
            qs = qs.filter(user_id=user_id)
        return qs


class ApplyMixin:
    """申请单公共逻辑：归属人、天数/时长计算、审批、我的 / 待我审批"""
    biz_type = None          # 关联的通用审批单类型
    calc_field = None        # 需要自动计算的字段：days / hours
    date_fields = ("start_at", "end_at")

    def perform_create(self, serializer):
        data = serializer.validated_data
        kwargs = {}
        if hasattr(serializer.Meta.model, "created_by"):
            kwargs["created_by"] = self.request.user
        if not data.get("user"):
            kwargs["user"] = self.request.user
        if self.calc_field and not data.get(self.calc_field):
            start = data.get(self.date_fields[0])
            end = data.get(self.date_fields[1])
            kwargs[self.calc_field] = (calc_hours(start, end) if self.calc_field == "hours"
                                       else calc_days(start, end))
        serializer.save(**kwargs)

    def perform_update(self, serializer):
        kwargs = {}
        if self.calc_field and not serializer.validated_data.get(self.calc_field):
            start = (serializer.validated_data.get(self.date_fields[0])
                     or getattr(serializer.instance, self.date_fields[0]))
            end = (serializer.validated_data.get(self.date_fields[1])
                   or getattr(serializer.instance, self.date_fields[1]))
            kwargs[self.calc_field] = (calc_hours(start, end) if self.calc_field == "hours"
                                       else calc_days(start, end))
        serializer.save(**kwargs)

    def sync_approval(self, obj, act, remark, now):
        """审批结果同步到关联的通用审批单"""
        if not self.biz_type:
            return
        approval = Approval.objects.filter(biz_type=self.biz_type, biz_id=obj.id).first()
        if not approval:
            return
        approval.status = "APPROVED" if act == "approve" else "REJECTED"
        approval.finished_at = now
        approval.save(update_fields=["status", "finished_at"])
        step = approval.steps.filter(step=approval.current_step).first()
        if step and step.status == "PENDING":
            step.status = "APPROVED" if act == "approve" else "REJECTED"
            step.approver = self.request.user
            step.remark = remark
            step.handled_at = now
            step.save()

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        """审批：action=approve/reject，remark=审批意见"""
        if not can_approve(request.user):
            return fail("无权限", code=403)
        obj = self.get_object()
        if obj.status not in ("DRAFT", "PENDING"):
            return fail("该申请已处理，无法重复审批")
        act = request.data.get("action")
        if act not in ("approve", "reject"):
            return fail("action 只能为 approve 或 reject")
        remark = request.data.get("remark", "")
        now = timezone.now()
        obj.approver = request.user
        obj.approved_at = now
        obj.status = "APPROVED" if act == "approve" else "REJECTED"
        if hasattr(obj, "approve_remark"):
            obj.approve_remark = remark
        obj.save()
        self.sync_approval(obj, act, remark, now)
        return ok(self.get_serializer(obj).data)

    @action(detail=False, methods=["get"], url_path="my")
    def my(self, request):
        """我发起的申请"""
        qs = self.filter_queryset(self.get_queryset()).filter(user=request.user)
        return ok(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="pending")
    def pending(self, request):
        """待我审批的申请"""
        if not can_approve(request.user):
            return fail("无权限", code=403)
        qs = (self.filter_queryset(self.get_queryset())
              .filter(status="PENDING", user__in=visible_user_ids(request.user)))
        return ok(self.get_serializer(qs, many=True).data)


class LeaveApplicationViewSet(ApplyMixin, ScopeModelViewSet):
    """请假申请"""
    queryset = LeaveApplication.objects.select_related("user", "approver").filter(is_deleted=False)
    serializer_class = LeaveApplicationSerializer
    owner_field = "user"
    biz_type = "LEAVE"
    calc_field = "days"

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        user_id = params.get("user")
        if user_id:
            qs = qs.filter(user_id=user_id)
        status_value = params.get("status")
        if status_value:
            qs = qs.filter(status=status_value)
        leave_type = params.get("leave_type")
        if leave_type:
            qs = qs.filter(leave_type=leave_type)
        return qs


class OvertimeApplicationViewSet(ApplyMixin, ScopeModelViewSet):
    """加班申请"""
    queryset = OvertimeApplication.objects.select_related("user", "approver").filter(is_deleted=False)
    serializer_class = OvertimeApplicationSerializer
    owner_field = "user"
    biz_type = "OVERTIME"
    calc_field = "hours"

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        user_id = params.get("user")
        if user_id:
            qs = qs.filter(user_id=user_id)
        status_value = params.get("status")
        if status_value:
            qs = qs.filter(status=status_value)
        return qs


class TravelApplicationViewSet(ApplyMixin, ScopeModelViewSet):
    """出差申请"""
    queryset = TravelApplication.objects.select_related("user", "approver").filter(is_deleted=False)
    serializer_class = TravelApplicationSerializer
    owner_field = "user"
    biz_type = "TRAVEL"
    calc_field = "days"

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        user_id = params.get("user")
        if user_id:
            qs = qs.filter(user_id=user_id)
        status_value = params.get("status")
        if status_value:
            qs = qs.filter(status=status_value)
        return qs


class ExpenseApplicationViewSet(ApplyMixin, ScopeModelViewSet):
    """报销申请"""
    queryset = ExpenseApplication.objects.select_related("user", "approver").filter(is_deleted=False)
    serializer_class = ExpenseApplicationSerializer
    owner_field = "user"
    biz_type = "EXPENSE"

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        user_id = params.get("user")
        if user_id:
            qs = qs.filter(user_id=user_id)
        category = params.get("category")
        if category:
            qs = qs.filter(category=category)
        status_value = params.get("status")
        if status_value:
            qs = qs.filter(status=status_value)
        return qs

    @action(detail=True, methods=["post"], url_path="pay")
    def pay(self, request, pk=None):
        """标记已支付（仅老板 / 人事）"""
        if not is_higher(request.user):
            return fail("无权限", code=403)
        obj = self.get_object()
        if obj.status != "APPROVED":
            return fail("只有已通过的报销单才能标记支付")
        obj.status = "PAID"
        obj.paid_at = timezone.now()
        obj.save(update_fields=["status", "paid_at"])
        return ok(self.get_serializer(obj).data)


class ApprovalViewSet(viewsets.ModelViewSet):
    """通用审批单"""
    queryset = (Approval.objects.filter(is_deleted=False)
                .select_related("applicant").prefetch_related("steps", "steps__approver"))
    serializer_class = ApprovalSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        biz_type = params.get("biz_type")
        if biz_type:
            qs = qs.filter(biz_type=biz_type)
        status_value = params.get("status")
        if status_value:
            qs = qs.filter(status=status_value)
        user_id = params.get("user")
        if user_id:
            qs = qs.filter(applicant_id=user_id)
        return qs

    def perform_create(self, serializer):
        """创建审批单，并按 steps 参数生成审批节点"""
        approval = serializer.save(applicant=self.request.user, created_by=self.request.user,
                                   status="PENDING", current_step=1)
        steps = self.request.data.get("steps")
        if isinstance(steps, list) and steps:
            for index, item in enumerate(steps, start=1):
                approver_id = item.get("approver") if isinstance(item, dict) else item
                ApprovalStep.objects.create(approval=approval, step=index, approver_id=approver_id)
        else:
            # 未指定节点时，默认一级审批：申请人所在部门负责人
            dept = self.request.user.department
            ApprovalStep.objects.create(
                approval=approval, step=1,
                approver_id=getattr(dept, "leader_id", None),
            )

    @action(detail=True, methods=["post"], url_path="handle")
    def handle(self, request, pk=None):
        """处理当前节点：action=approve/reject，remark=审批意见"""
        approval = self.get_object()
        if approval.status != "PENDING":
            return fail("该审批单已结束，无法处理")
        step = approval.steps.filter(step=approval.current_step).first()
        if not step:
            return fail("审批节点不存在")
        if step.approver_id != request.user.id and not request.user.is_superuser:
            return fail("无权限", code=403)
        act = request.data.get("action")
        if act not in ("approve", "reject"):
            return fail("action 只能为 approve 或 reject")
        remark = request.data.get("remark", "")
        now = timezone.now()

        if act == "reject":
            step.status = "REJECTED"
            step.remark = remark
            step.handled_at = now
            step.save()
            approval.status = "REJECTED"
            approval.finished_at = now
            approval.save(update_fields=["status", "finished_at"])
            return ok(ApprovalSerializer(approval).data, msg="已驳回")

        step.status = "APPROVED"
        step.remark = remark
        step.handled_at = now
        step.save()
        next_step = approval.steps.filter(step__gt=approval.current_step).order_by("step").first()
        if next_step:
            approval.current_step = next_step.step
            approval.save(update_fields=["current_step"])
        else:
            approval.status = "APPROVED"
            approval.finished_at = now
            approval.save(update_fields=["status", "finished_at"])
        return ok(ApprovalSerializer(approval).data, msg="已同意")

    @action(detail=False, methods=["get"], url_path="todo")
    def todo(self, request):
        """待我审批的单子：当前节点审批人是我且尚未处理"""
        qs = (self.filter_queryset(self.get_queryset())
              .filter(status="PENDING", steps__approver=request.user).distinct())
        items = []
        for approval in qs:
            for step in approval.steps.all():
                if (step.step == approval.current_step and step.status == "PENDING"
                        and step.approver_id == request.user.id):
                    items.append(approval)
                    break
        return ok(self.get_serializer(items, many=True).data)

    @action(detail=False, methods=["get"], url_path="my")
    def my(self, request):
        """我发起的审批"""
        qs = self.filter_queryset(self.get_queryset()).filter(applicant=request.user)
        return ok(ApprovalSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="done")
    def done(self, request):
        """我已处理的审批"""
        qs = (self.filter_queryset(self.get_queryset())
              .filter(steps__approver=request.user, steps__status__in=["APPROVED", "REJECTED"])
              .distinct())
        return ok(ApprovalSerializer(qs, many=True).data)


class ApprovalStepViewSet(viewsets.ReadOnlyModelViewSet):
    """审批节点（只读）"""
    queryset = ApprovalStep.objects.select_related("approver").filter(is_deleted=False)
    serializer_class = ApprovalStepSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        approval_id = self.request.query_params.get("approval")
        if approval_id:
            qs = qs.filter(approval_id=approval_id)
        return qs


# ==================== 全公司薪酬绩效核算 ====================
# 说明：薪酬绩效模块由电销部迁移至人事考勤，计算口径与公司标准保持一致
# （底薪 3500 已含全勤，阶梯提成沿用 COMPANY_LADDER）。差异在于：
#   1) 覆盖全公司所有在职员工，不再仅限电销部
#   2) 支持按部门筛选、全员批量核算、部门维度汇总

class SalaryViewSet(viewsets.ModelViewSet):
    """全公司全员薪酬绩效核算"""
    queryset = SalaryRecord.objects.filter(is_deleted=False)
    serializer_class = SalaryRecordSerializer
    search_fields = ["user__username", "user__first_name", "month"]
    ordering_fields = ["month", "total", "performance"]

    def get_queryset(self):
        qs = super().get_queryset().select_related("user", "user__department")
        user = self.request.user
        if user.is_superuser or user.role in ("BOSS", "HR"):
            pass
        elif user.role in ("MANAGER", "LEADER"):
            qs = qs.filter(user_id__in=visible_user_ids(user))
        else:
            qs = qs.filter(user=user)

        params = self.request.query_params
        month = params.get("month")
        if month:
            qs = qs.filter(month=month)
        department = params.get("department")
        if department:
            qs = qs.filter(user__department_id=department)
        uid = params.get("user") or params.get("user_id")
        if uid:
            qs = qs.filter(user_id=uid)
        settled = params.get("settled")
        if settled in ("true", "True", "1"):
            qs = qs.filter(settled=True)
        elif settled in ("false", "False", "0"):
            qs = qs.filter(settled=False)
        keyword = params.get("keyword")
        if keyword:
            qs = qs.filter(Q(user__username__icontains=keyword)
                           | Q(user__first_name__icontains=keyword)
                           | Q(user__last_name__icontains=keyword)
                           | Q(user__employee_no__icontains=keyword))
        return qs

    @staticmethod
    def _calc_one(user, month, performance=0, bonus=0, deduction=0):
        """核算单个员工工资明细（与电销部口径一致）"""
        base_salary = user.base_salary if user.base_salary else Decimal("3500")
        rule = CommissionRule(rule_type="LADDER", ladder=COMPANY_LADDER, name="公司标准阶梯提成")
        commission, rule_name = calc_commission(rule, performance)
        base_salary = Decimal(str(base_salary))
        bonus = Decimal(str(bonus))
        deduction = Decimal(str(deduction))
        commission = Decimal(str(commission))
        total = base_salary + commission + bonus - deduction
        return {
            "user": user.id,
            "user_id": user.id,
            "user_name": user.display_name,
            "department": user.department_id,
            "department_name": getattr(user.department, "name", "") or "",
            "month": month,
            "base_salary": float(base_salary),
            "performance": float(Decimal(str(performance or 0))),
            "commission": float(commission),
            "commission_rule": rule_name,
            "bonus": float(bonus),
            "deduction": float(deduction),
            "total": float(total),
        }

    @action(detail=False, methods=["post"], url_path="calc", permission_classes=[IsHR])
    def calc(self, request):
        """单人核算：{user_id, month, performance, bonus, deduction}"""
        uid = request.data.get("user_id") or request.data.get("user")
        month = request.data.get("month") or timezone.localdate().strftime("%Y-%m")
        if not uid:
            return Response({"code": 1, "msg": "请选择员工"}, status=400)
        user = User.objects.filter(id=uid, is_active=True).first()
        if not user:
            return Response({"code": 1, "msg": "员工不存在或已停用"}, status=400)
        return Response({"code": 0, "msg": "ok", "data": self._calc_one(
            user, month,
            request.data.get("performance") or 0,
            request.data.get("bonus") or 0,
            request.data.get("deduction") or 0,
        )})

    @action(detail=False, methods=["post"], url_path="batch-calc")
    def batch_calc(self, request):
        """全员批量核算：{month} —— 按该月已录业绩自动算薪并落库（已存在的更新）"""
        if not is_higher(request.user):
            raise PermissionDenied("仅老板/人事可执行全员核算")
        month = request.data.get("month") or timezone.localdate().strftime("%Y-%m")
        users = User.objects.filter(is_active=True).exclude(status="RESIGNED")
        count = 0
        for u in users:
            # 业绩口径：该员工当月作为销售签署的合同金额
            performance = Contract.objects.filter(
                is_deleted=False, sales=u, signed_date__year=month[:4], signed_date__month=month[5:7],
            ).aggregate(total=Sum("amount"))["total"] or 0
            detail = self._calc_one(u, month, performance)
            rec = SalaryRecord.objects.filter(user=u, month=month, is_deleted=False).first()
            payload = {
                "base_salary": detail["base_salary"],
                "performance": detail["performance"],
                "commission": detail["commission"],
                "commission_rule": detail["commission_rule"],
                "total": detail["total"],
            }
            if rec:
                for k, v in payload.items():
                    setattr(rec, k, v)
                rec.save()
            else:
                SalaryRecord.objects.create(
                    user=u, month=month, created_by=request.user,
                    bonus=0, deduction=0, **payload)
            count += 1
        return Response({"code": 0, "msg": f"已完成 {count} 人核算", "data": {"count": count, "month": month}})

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """月度薪酬汇总：人数、总额、提成、人均、部门分布"""
        month = request.query_params.get("month") or timezone.localdate().strftime("%Y-%m")
        qs = self.get_queryset().filter(month=month)
        amount = qs.aggregate(s=Sum("total"), c=Sum("commission"), n=Count("id"))
        headcount = amount["n"] or 0
        total_amount = float(amount["s"] or 0)
        total_commission = float(amount["c"] or 0)
        departments = []
        rows = (qs.values("user__department__name")
                   .annotate(headcount=Count("id"), total=Sum("total"))
                   .order_by("-total"))
        for r in rows:
            total = float(r["total"] or 0)
            departments.append({
                "name": r["user__department__name"] or "未分配",
                "headcount": r["headcount"],
                "total": total,
                "avg": round(total / r["headcount"], 2) if r["headcount"] else 0,
            })
        return Response({"code": 0, "msg": "ok", "data": {
            "month": month,
            "headcount": headcount,
            "total_amount": total_amount,
            "total_commission": total_commission,
            "avg_amount": round(total_amount / headcount, 2) if headcount else 0,
            "departments": departments,
        }})

    @action(detail=False, methods=["get"], url_path="my")
    def my(self, request):
        """我的工资条"""
        month = request.query_params.get("month")
        qs = SalaryRecord.objects.filter(is_deleted=False, user=request.user)
        if month:
            qs = qs.filter(month=month)
        return Response({"code": 0, "msg": "ok",
                         "data": SalaryRecordSerializer(qs.order_by("-month"), many=True).data})

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


# ==================== 人事业绩 · 业绩统计 ====================

@api_view(["GET"])
def performance_stat(request):
    """个人 / 部门 周期业绩统计。

    参数：month(YYYY-MM)、scope(PERSON|DEPT)、department、user
    """
    month = request.GET.get("month") or timezone.localdate().strftime("%Y-%m")
    scope = (request.GET.get("scope") or "PERSON").upper()
    year, mon = month[:4], month[5:7]
    user = request.user

    # 可见范围
    if user.is_superuser or user.role in ("BOSS", "HR"):
        users = User.objects.filter(is_active=True)
    elif user.role in ("MANAGER", "LEADER"):
        users = User.objects.filter(id__in=visible_user_ids(user))
    else:
        users = User.objects.filter(id=user.id)

    dept_id = request.GET.get("department")
    if dept_id:
        users = users.filter(department_id=dept_id)
    uid = request.GET.get("user")
    if uid:
        users = users.filter(id=uid)

    contract_filter = Q(is_deleted=False, signed_date__year=year, signed_date__month=mon)
    lead_filter = Q(is_deleted=False, dealt_at__year=year, dealt_at__month=mon)
    customer_filter = Q(is_deleted=False, created_at__year=year, created_at__month=mon)
    call_filter = Q(user__in=users, created_at__year=year, created_at__month=mon)

    def pct(actual, target):
        if not target:
            return None
        return round(float(actual) / float(target) * 100, 1)

    targets = {}
    for t in SalesTarget.objects.filter(month=month, scope="PERSON"):
        targets[t.user_id] = float(t.amount_target or 0)
    dept_targets = {}
    for t in SalesTarget.objects.filter(month=month, scope="DEPARTMENT"):
        dept_targets[t.department_id] = float(t.amount_target or 0)

    rows = []
    if scope == "DEPT":
        dept_ids = list(users.values_list("department_id", flat=True).distinct())
        for did in dept_ids:
            if not did:
                continue
            from apps.accounts.models import Department
            dept = Department.objects.filter(id=did).first()
            members = users.filter(department_id=did)
            amount = Contract.objects.filter(contract_filter, sales__in=members).aggregate(
                s=Sum("amount"))["s"] or 0
            deals = Contract.objects.filter(contract_filter, sales__in=members).count()
            new_cust = Customer.objects.filter(customer_filter, owner__in=members).count()
            calls = CallRecord.objects.filter(call_filter, user__in=members).count()
            target = dept_targets.get(did) or sum(targets.get(m.id, 0) for m in members)
            rows.append({
                "department_id": did,
                "department_name": dept.name if dept else "未分配",
                "headcount": members.count(),
                "contract_amount": float(amount),
                "deal_count": deals,
                "new_customer_count": new_cust,
                "call_count": calls,
                "target": float(target),
                "achieve_rate": pct(amount, target),
            })
    else:
        for u in users.select_related("department"):
            amount = Contract.objects.filter(contract_filter, sales=u).aggregate(s=Sum("amount"))["s"] or 0
            deals = Contract.objects.filter(contract_filter, sales=u).count()
            new_cust = Customer.objects.filter(customer_filter, owner=u).count()
            calls = CallRecord.objects.filter(call_filter, user=u).count()
            target = targets.get(u.id, 0)
            rows.append({
                "user_id": u.id,
                "user_name": u.display_name,
                "department_id": u.department_id,
                "department_name": getattr(u.department, "name", "") or "",
                "contract_amount": float(amount),
                "deal_count": deals,
                "new_customer_count": new_cust,
                "call_count": calls,
                "target": target,
                "achieve_rate": pct(amount, target),
            })

    rows.sort(key=lambda r: -(r.get("contract_amount") or 0))
    total_amount = sum(r["contract_amount"] for r in rows)
    total_target = sum(r["target"] for r in rows)
    return Response({"code": 0, "msg": "ok", "data": {
        "month": month,
        "scope": scope,
        "list": rows,
        "summary": {
            "total_amount": round(total_amount, 2),
            "total_deal": sum(r["deal_count"] for r in rows),
            "total_customer": sum(r["new_customer_count"] for r in rows),
            "total_call": sum(r["call_count"] for r in rows),
            "total_target": round(total_target, 2),
            "achieve_rate": pct(total_amount, total_target),
        },
    }})


# ==================== 钉钉缺失功能补全：视图集 ====================

class HrApproveMixin:
    """人事类申请单通用审批：approve / reject（仅老板 / 人事 / 主管可审批）"""
    def _apply_decision(self, obj, act, remark, now):
        obj.status = "APPROVED" if act == "approve" else "REJECTED"
        obj.approved_at = now
        obj.approver = self.request.user
        if hasattr(obj, "approve_remark"):
            obj.approve_remark = remark
        obj.save()

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        if not can_approve(request.user):
            return fail("无权限", code=403)
        obj = self.get_object()
        if obj.status not in ("PENDING",):
            return fail("该申请已处理，无法重复审批")
        act = request.data.get("action")
        if act not in ("approve", "reject"):
            return fail("action 只能为 approve 或 reject")
        remark = request.data.get("remark", "")
        self._apply_decision(obj, act, remark, timezone.now())
        return ok(self.get_serializer(obj).data)


class JobLevelViewSet(viewsets.ModelViewSet):
    """岗位职级库（管理 / 销售 / 财务会计 / 运营主播序列）"""
    queryset = JobLevel.objects.filter(is_deleted=False).order_by("sequence", "level")
    serializer_class = JobLevelSerializer
    search_fields = ["name"]


class ExternalContactViewSet(ScopeModelViewSet):
    """外部联系人（客户 / 渠道合作方），区别于内部员工通讯录"""
    queryset = ExternalContact.objects.filter(is_deleted=False)
    serializer_class = ExternalContactSerializer
    owner_field = "owner"
    search_fields = ["name", "company", "phone"]


class UserAttachmentViewSet(ScopeModelViewSet):
    """员工证件 / 材料附件"""
    queryset = UserAttachment.objects.filter(is_deleted=False)
    serializer_class = UserAttachmentSerializer
    owner_field = "user"
    search_fields = ["category", "remark"]


class EmployeeChangeLogViewSet(ScopeModelViewSet):
    """员工资料变更记录（只读留痕）"""
    queryset = EmployeeChangeLog.objects.filter(is_deleted=False).order_by("-created_at")
    serializer_class = EmployeeChangeLogSerializer
    owner_field = "user"

    def get_queryset(self):
        qs = super().get_queryset()
        uid = self.request.query_params.get("user")
        if uid:
            qs = qs.filter(user_id=uid)
        return qs


class LaborContractViewSet(ScopeModelViewSet):
    """劳动合同台账（独立于销售合同）"""
    queryset = LaborContract.objects.filter(is_deleted=False).order_by("-signed_date")
    serializer_class = LaborContractSerializer
    owner_field = "user"
    search_fields = ["contract_no"]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        ctype = params.get("contract_type")
        if ctype:
            qs = qs.filter(contract_type=ctype)
        status_value = params.get("status")
        if status_value:
            qs = qs.filter(status=status_value)
        return qs

    @action(detail=False, methods=["get"], url_path="expiring")
    def expiring(self, request):
        """合同到期预警：N 天内到期且仍生效中"""
        from datetime import timedelta
        days = int(request.query_params.get("days", 30))
        until = timezone.localdate() + timedelta(days=days)
        qs = self.filter_queryset(self.get_queryset()).filter(
            status="ACTIVE", end_date__isnull=False, end_date__lte=until,
            end_date__gte=timezone.localdate())
        return ok(self.get_serializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="renew")
    def renew(self, request, pk=None):
        """发起续签：复制为新的续签合同"""
        if not is_higher(request.user):
            return fail("无权限", code=403)
        old = self.get_object()
        new = LaborContract.objects.create(
            user=old.user, contract_type=old.contract_type,
            contract_no=(old.contract_no + "-续"), is_renewal=True, renewal_of=old,
            start_date=old.end_date, status="ACTIVE",
            created_by=request.user)
        old.status = "RENEWED"
        old.save(update_fields=["status"])
        return ok(self.get_serializer(new).data, msg="已生成续签合同")


class RegularizationApplicationViewSet(HrApproveMixin, ScopeModelViewSet):
    """转正申请"""
    queryset = RegularizationApplication.objects.filter(is_deleted=False).order_by("-created_at")
    serializer_class = RegularizationApplicationSerializer
    owner_field = "user"

    def get_queryset(self):
        qs = super().get_queryset()
        status_value = self.request.query_params.get("status")
        if status_value:
            qs = qs.filter(status=status_value)
        return qs


class TransferApplicationViewSet(HrApproveMixin, ScopeModelViewSet):
    """异动调岗 / 调级（审批通过自动同步通讯录）"""
    queryset = TransferApplication.objects.filter(is_deleted=False).order_by("-created_at")
    serializer_class = TransferApplicationSerializer
    owner_field = "user"

    def get_queryset(self):
        qs = super().get_queryset()
        status_value = self.request.query_params.get("status")
        if status_value:
            qs = qs.filter(status=status_value)
        return qs


class ResignApplicationViewSet(HrApproveMixin, ScopeModelViewSet):
    """离职申请 + 工作交接（审批通过自动调整通讯录状态）"""
    queryset = ResignApplication.objects.filter(is_deleted=False).order_by("-created_at")
    serializer_class = ResignApplicationSerializer
    owner_field = "user"

    def get_queryset(self):
        qs = super().get_queryset()
        status_value = self.request.query_params.get("status")
        if status_value:
            qs = qs.filter(status=status_value)
        return qs


class AttendanceGroupViewSet(viewsets.ModelViewSet):
    """考勤组（按部门划分）"""
    queryset = AttendanceGroup.objects.filter(is_deleted=False).order_by("name")
    serializer_class = AttendanceGroupSerializer
    search_fields = ["name"]


class ShiftScheduleViewSet(ScopeModelViewSet):
    """排班（适配销售 / 主播轮班倒班）"""
    queryset = ShiftSchedule.objects.all()
    serializer_class = ShiftScheduleSerializer
    owner_field = "user"

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        uid = params.get("user")
        if uid:
            qs = qs.filter(user_id=uid)
        date = params.get("date")
        if date:
            qs = qs.filter(date=date)
        month = params.get("month")
        if month:
            qs = qs.filter(date__startswith=month)
        return qs


class LeaveBalanceViewSet(ScopeModelViewSet):
    """假期余额（自动核算）"""
    queryset = LeaveBalance.objects.filter(is_deleted=False).order_by("-year")
    serializer_class = LeaveBalanceSerializer
    owner_field = "user"

    def get_queryset(self):
        qs = super().get_queryset()
        uid = self.request.query_params.get("user")
        if uid:
            qs = qs.filter(user_id=uid)
        year = self.request.query_params.get("year")
        if year:
            qs = qs.filter(year=year)
        return qs


class PurchaseApplicationViewSet(HrApproveMixin, ScopeModelViewSet):
    """采购申请"""
    queryset = PurchaseApplication.objects.filter(is_deleted=False).order_by("-created_at")
    serializer_class = PurchaseApplicationSerializer
    owner_field = "applicant"

    def get_queryset(self):
        qs = super().get_queryset()
        status_value = self.request.query_params.get("status")
        if status_value:
            qs = qs.filter(status=status_value)
        return qs


class SealApplicationViewSet(HrApproveMixin, ScopeModelViewSet):
    """用印申请"""
    queryset = SealApplication.objects.filter(is_deleted=False).order_by("-created_at")
    serializer_class = SealApplicationSerializer
    owner_field = "applicant"

    def get_queryset(self):
        qs = super().get_queryset()
        status_value = self.request.query_params.get("status")
        if status_value:
            qs = qs.filter(status=status_value)
        return qs


class PerformancePlanViewSet(viewsets.ModelViewSet):
    """绩效方案配置（支持分部门）"""
    queryset = PerformancePlan.objects.filter(is_deleted=False).order_by("-is_active", "name")
    serializer_class = PerformancePlanSerializer
    search_fields = ["name"]


class PerformanceReviewViewSet(ScopeModelViewSet):
    """绩效考核：发起 / 评分 / 归档"""
    queryset = PerformanceReview.objects.filter(is_deleted=False).order_by("-created_at")
    serializer_class = PerformanceReviewSerializer
    owner_field = "user"

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        uid = params.get("user")
        if uid:
            qs = qs.filter(user_id=uid)
        status_value = params.get("status")
        if status_value:
            qs = qs.filter(status=status_value)
        period = params.get("period")
        if period:
            qs = qs.filter(period=period)
        return qs


class AddressBookVisibilityViewSet(viewsets.ModelViewSet):
    """通讯录可见权限配置"""
    queryset = AddressBookVisibility.objects.filter(is_deleted=False)
    serializer_class = AddressBookVisibilitySerializer
    search_fields = ["name"]


class RolePresetViewSet(viewsets.ModelViewSet):
    """角色权限预设矩阵"""
    queryset = RolePreset.objects.filter(is_deleted=False)
    serializer_class = RolePresetSerializer
