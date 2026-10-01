"""人事考勤与审批：序列化器"""
from rest_framework import serializers
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


class JobLevelSerializer(serializers.ModelSerializer):
    sequence_name = serializers.CharField(source="get_sequence_display", read_only=True)

    class Meta:
        model = JobLevel
        fields = ["id", "name", "sequence", "sequence_name", "level", "description", "created_at"]


class ExternalContactSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source="get_group_display", read_only=True)
    owner_name = serializers.CharField(source="owner.display_name", read_only=True)

    class Meta:
        model = ExternalContact
        fields = ["id", "name", "group", "group_name", "company", "phone", "wechat",
                  "position", "owner", "owner_name", "remark", "created_at"]


class UserAttachmentSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="get_category_display", read_only=True)
    user_name = serializers.CharField(source="user.display_name", read_only=True)

    class Meta:
        model = UserAttachment
        fields = ["id", "user", "user_name", "category", "category_name", "file", "remark", "created_at"]


class EmployeeChangeLogSerializer(serializers.ModelSerializer):
    action_name = serializers.CharField(source="get_action_display", read_only=True)
    user_name = serializers.CharField(source="user.display_name", read_only=True)
    operator_name = serializers.CharField(source="operator.display_name", read_only=True)

    class Meta:
        model = EmployeeChangeLog
        fields = ["id", "user", "user_name", "action", "action_name", "field",
                  "old_value", "new_value", "operator", "operator_name", "remark", "created_at"]


class LaborContractSerializer(serializers.ModelSerializer):
    type_name = serializers.CharField(source="get_contract_type_display", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)
    user_name = serializers.CharField(source="user.display_name", read_only=True)

    class Meta:
        model = LaborContract
        fields = ["id", "user", "user_name", "contract_type", "type_name", "contract_no",
                  "start_date", "end_date", "signed_date", "status", "status_name",
                  "is_renewal", "renewal_of", "attachment", "remark", "created_at"]


class RegularizationApplicationSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.display_name", read_only=True)
    approver_name = serializers.CharField(source="approver.display_name", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = RegularizationApplication
        fields = ["id", "user", "user_name", "probation_end", "apply_date", "summary",
                  "status", "status_name", "approver", "approver_name",
                  "approved_at", "approve_remark", "approval", "created_at"]
        extra_kwargs = {"user": {"required": False}}


class TransferApplicationSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.display_name", read_only=True)
    from_department_name = serializers.CharField(source="from_department.name", read_only=True)
    to_department_name = serializers.CharField(source="to_department.name", read_only=True)
    from_position_name = serializers.CharField(source="from_position.name", read_only=True)
    to_position_name = serializers.CharField(source="to_position.name", read_only=True)
    from_job_level_name = serializers.CharField(source="from_job_level.name", read_only=True)
    to_job_level_name = serializers.CharField(source="to_job_level.name", read_only=True)
    approver_name = serializers.CharField(source="approver.display_name", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = TransferApplication
        fields = ["id", "user", "user_name", "from_department", "from_department_name",
                  "to_department", "to_department_name", "from_position", "from_position_name",
                  "to_position", "to_position_name", "from_job_level", "from_job_level_name",
                  "to_job_level", "to_job_level_name", "reason", "status", "status_name",
                  "approver", "approver_name", "approved_at", "approve_remark",
                  "approval", "created_at"]
        extra_kwargs = {"user": {"required": False}}


class ResignApplicationSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.display_name", read_only=True)
    handover_to_name = serializers.CharField(source="handover_to.display_name", read_only=True)
    approver_name = serializers.CharField(source="approver.display_name", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ResignApplication
        fields = ["id", "user", "user_name", "resign_date", "reason_type", "reason",
                  "handover_to", "handover_to_name", "handover_items", "status", "status_name",
                  "approver", "approver_name", "approved_at", "approve_remark",
                  "approval", "created_at"]
        extra_kwargs = {"user": {"required": False}}


class AttendanceGroupSerializer(serializers.ModelSerializer):
    department_names = serializers.SerializerMethodField()
    rule_name = serializers.CharField(source="rule.name", read_only=True)

    class Meta:
        model = AttendanceGroup
        fields = ["id", "name", "departments", "department_names", "rule", "rule_name",
                  "description", "created_at"]

    def get_department_names(self, obj):
        return [d.name for d in obj.departments.all()]


class ShiftScheduleSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.display_name", read_only=True)
    shift_name = serializers.CharField(source="get_shift_display", read_only=True)

    class Meta:
        model = ShiftSchedule
        fields = ["id", "user", "user_name", "date", "shift", "shift_name", "note", "created_at"]


class LeaveBalanceSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.display_name", read_only=True)

    class Meta:
        model = LeaveBalance
        fields = ["id", "user", "user_name", "year", "annual_total", "annual_used",
                  "personal_total", "personal_used", "compensate_total", "compensate_used",
                  "created_at"]


class PurchaseApplicationSerializer(serializers.ModelSerializer):
    applicant_name = serializers.CharField(source="applicant.display_name", read_only=True)
    approver_name = serializers.CharField(source="approver.display_name", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PurchaseApplication
        fields = ["id", "applicant", "applicant_name", "item_name", "spec", "quantity",
                  "amount", "purpose", "supplier", "status", "status_name", "approver",
                  "approver_name", "approved_at", "approval", "created_at"]
        extra_kwargs = {"applicant": {"required": False}}


class SealApplicationSerializer(serializers.ModelSerializer):
    applicant_name = serializers.CharField(source="applicant.display_name", read_only=True)
    approver_name = serializers.CharField(source="approver.display_name", read_only=True)
    type_name = serializers.CharField(source="get_seal_type_display", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = SealApplication
        fields = ["id", "applicant", "applicant_name", "seal_type", "type_name", "doc_name",
                  "reason", "use_date", "status", "status_name", "approver", "approver_name",
                  "approved_at", "approval", "created_at"]
        extra_kwargs = {"applicant": {"required": False}}


class PerformancePlanSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    cycle_name = serializers.CharField(source="get_cycle_display", read_only=True)

    class Meta:
        model = PerformancePlan
        fields = ["id", "name", "department", "department_name", "cycle", "cycle_name",
                  "template", "is_active", "created_at"]


class PerformanceReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.display_name", read_only=True)
    reviewer_name = serializers.CharField(source="reviewer.display_name", read_only=True)
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PerformanceReview
        fields = ["id", "plan", "plan_name", "user", "user_name", "reviewer", "reviewer_name",
                  "period", "score", "grade", "result", "status", "status_name", "created_at"]


class AddressBookVisibilitySerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = AddressBookVisibility
        fields = ["id", "name", "role", "role_name", "can_see_departments",
                  "see_all", "see_self_dept", "created_at"]


class RolePresetSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = RolePreset
        fields = ["id", "role", "role_name", "can_view_addressbook", "can_view_archives",
                  "can_view_salary", "can_view_contract", "can_view_performance",
                  "can_manage_attendance", "can_approve", "description", "created_at"]


class AttendanceRuleSerializer(serializers.ModelSerializer):
    """考勤规则"""

    class Meta:
        model = AttendanceRule
        fields = ["id", "name", "work_start", "work_end", "late_minutes", "late_penalty",
                  "absent_penalty", "work_days", "is_default", "created_at", "updated_at"]


class AttendanceSerializer(serializers.ModelSerializer):
    """考勤记录"""
    user_name = serializers.CharField(source="user.display_name", read_only=True)
    department_name = serializers.CharField(source="user.department.name", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Attendance
        fields = ["id", "user", "user_name", "department_name", "date",
                  "check_in", "check_out", "check_in_location", "check_out_location",
                  "status", "status_name", "late_minutes", "work_hours", "remark"]
        extra_kwargs = {"user": {"required": False}}


class AttendanceStatSerializer(serializers.ModelSerializer):
    """考勤月报"""
    user_name = serializers.CharField(source="user.display_name", read_only=True)
    department_name = serializers.CharField(source="user.department.name", read_only=True)

    class Meta:
        model = AttendanceStat
        fields = ["id", "user", "user_name", "department_name", "month",
                  "normal_days", "late_times", "early_times", "absent_days",
                  "leave_days", "overtime_hours", "penalty", "updated_at"]


class LeaveApplicationSerializer(serializers.ModelSerializer):
    """请假申请"""
    user_name = serializers.CharField(source="user.display_name", read_only=True)
    department_name = serializers.CharField(source="user.department.name", read_only=True)
    approver_name = serializers.CharField(source="approver.display_name", read_only=True)
    leave_type_name = serializers.CharField(source="get_leave_type_display", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = LeaveApplication
        fields = ["id", "user", "user_name", "department_name", "leave_type", "leave_type_name",
                  "start_at", "end_at", "days", "reason", "attachment",
                  "status", "status_name", "approver", "approver_name",
                  "approved_at", "approve_remark", "created_at"]
        extra_kwargs = {"user": {"required": False}}


class OvertimeApplicationSerializer(serializers.ModelSerializer):
    """加班申请"""
    user_name = serializers.CharField(source="user.display_name", read_only=True)
    department_name = serializers.CharField(source="user.department.name", read_only=True)
    approver_name = serializers.CharField(source="approver.display_name", read_only=True)
    compensate_name = serializers.CharField(source="get_compensate_display", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = OvertimeApplication
        fields = ["id", "user", "user_name", "department_name", "start_at", "end_at", "hours",
                  "reason", "compensate", "compensate_name", "status", "status_name",
                  "approver", "approver_name", "approved_at", "created_at"]
        extra_kwargs = {"user": {"required": False}}


class TravelApplicationSerializer(serializers.ModelSerializer):
    """出差申请"""
    user_name = serializers.CharField(source="user.display_name", read_only=True)
    department_name = serializers.CharField(source="user.department.name", read_only=True)
    approver_name = serializers.CharField(source="approver.display_name", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = TravelApplication
        fields = ["id", "user", "user_name", "department_name", "destination",
                  "start_at", "end_at", "days", "reason", "budget",
                  "status", "status_name", "approver", "approver_name",
                  "approved_at", "created_at"]
        extra_kwargs = {"user": {"required": False}}


class ExpenseApplicationSerializer(serializers.ModelSerializer):
    """报销申请"""
    user_name = serializers.CharField(source="user.display_name", read_only=True)
    department_name = serializers.CharField(source="user.department.name", read_only=True)
    approver_name = serializers.CharField(source="approver.display_name", read_only=True)
    category_name = serializers.CharField(source="get_category_display", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ExpenseApplication
        fields = ["id", "user", "user_name", "department_name", "category", "category_name",
                  "amount", "happened_at", "reason", "invoice_no", "attachment",
                  "status", "status_name", "approver", "approver_name",
                  "approved_at", "paid_at", "created_at"]
        extra_kwargs = {"user": {"required": False}}


class ApprovalStepSerializer(serializers.ModelSerializer):
    """审批节点"""
    approver_name = serializers.CharField(source="approver.display_name", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ApprovalStep
        fields = ["id", "approval", "step", "approver", "approver_name",
                  "status", "status_name", "remark", "handled_at", "created_at"]


class ApprovalSerializer(serializers.ModelSerializer):
    """通用审批单"""
    applicant_name = serializers.CharField(source="applicant.display_name", read_only=True)
    department_name = serializers.CharField(source="applicant.department.name", read_only=True)
    biz_type_name = serializers.CharField(source="get_biz_type_display", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)
    steps = ApprovalStepSerializer(many=True, read_only=True)
    current_approver_name = serializers.SerializerMethodField()

    class Meta:
        model = Approval
        fields = ["id", "biz_type", "biz_type_name", "biz_id", "title", "content",
                  "applicant", "applicant_name", "department_name",
                  "status", "status_name", "current_step", "current_approver_name",
                  "steps", "finished_at", "created_at"]
        extra_kwargs = {"applicant": {"required": False}}

    def get_current_approver_name(self, obj):
        """当前待审批节点的审批人"""
        for step in obj.steps.all():
            if step.step == obj.current_step and step.status == "PENDING" and step.approver:
                return step.approver.display_name
        return ""
