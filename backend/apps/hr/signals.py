"""钉钉缺失功能补全：自动同步信号

权责：行政人事部；最高审批：总经办。
- 入职申请通过 → 自动创建员工档案(User)
- 转正申请通过 → 员工状态置「正式」+ 变更留痕
- 调岗申请通过 → 自动同步通讯录(部门/岗位/职级) + 变更留痕
- 离职申请通过 → 通讯录状态置「已离职」+ 交接台账留痕
- 请假审批通过 → 自动回写假期余额
"""
from datetime import timedelta

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.accounts.models import User, Department, EntryApplication
from .models import (
    RegularizationApplication, TransferApplication,
    ResignApplication, LeaveApplication, ExpenseApplication,
    EmployeeChangeLog, LeaveBalance,
)


# ---------- 状态变更前捕获旧值 ----------
@receiver(pre_save, sender=RegularizationApplication)
@receiver(pre_save, sender=TransferApplication)
@receiver(pre_save, sender=ResignApplication)
# 2026-10-02 增量：请假/报销也需要旧状态，用于判断是否刚发生审批结果变更（仅推送一次）
@receiver(pre_save, sender=LeaveApplication)
@receiver(pre_save, sender=ExpenseApplication)
def _capture_old_status(sender, instance, **kwargs):
    if instance.pk:
        old = sender.objects.filter(pk=instance.pk).only("status").first()
        instance._old_status = old.status if old else None
    else:
        instance._old_status = None


# ---------- 入职申请通过：自动建档 ----------
@receiver(post_save, sender=EntryApplication)
def _entry_approved_create_user(sender, instance, created, **kwargs):
    if instance.status != "APPROVED":
        return
    if getattr(instance, "_entry_synced", False):
        return
    phone = (instance.phone or "").strip()
    existing = None
    if phone:
        existing = User.objects.filter(phone=phone).first()
    if existing:
        instance._entry_synced = True
        return
    username = phone or f"emp_{int(timezone.now().timestamp())}"
    user = User(
        username=username,
        employee_no=username,
        first_name=instance.applicant_name,
        phone=phone or None,
        id_card_no=instance.id_card_no or "",
        department=instance.proposed_department,
        position=instance.proposed_position,
        role="EMPLOYEE",
        status="PROBATION",
        entry_date=timezone.localdate(),
        is_active=True,
    )
    # 预览态默认口令，正式上线应强制重置
    user.set_password("finops123")
    user.save()
    EmployeeChangeLog.objects.create(
        user=user, action="CREATE", operator=instance.reviewed_by,
        remark="入职申请审核通过，自动创建人事档案")
    instance._entry_synced = True


# ---------- 转正通过：置正式 ----------
@receiver(post_save, sender=RegularizationApplication)
def _regularization_approved(sender, instance, created, **kwargs):
    if instance.status == "APPROVED" and getattr(instance, "_old_status", None) != "APPROVED":
        u = instance.user
        if u and u.status != "REGULAR":
            u.status = "REGULAR"
            u.regular_date = instance.apply_date or timezone.localdate()
            u.save(update_fields=["status", "regular_date"])
            EmployeeChangeLog.objects.create(
                user=u, action="REGULAR", operator=instance.approver,
                remark="试用期转正，自动更新在职状态")


# ---------- 调岗通过：同步通讯录 ----------
@receiver(post_save, sender=TransferApplication)
def _transfer_approved(sender, instance, created, **kwargs):
    if instance.status == "APPROVED" and getattr(instance, "_old_status", None) != "APPROVED":
        u = instance.user
        if not u:
            return
        old_dept = u.department_id
        old_pos = u.position_id
        old_jl = u.job_level_id
        if instance.to_department_id:
            u.department_id = instance.to_department_id
        if instance.to_position_id:
            u.position_id = instance.to_position_id
        if instance.to_job_level_id:
            u.job_level_id = instance.to_job_level_id
        u.save()
        changed = []
        if old_dept != u.department_id:
            changed.append(f"部门 {old_dept}→{u.department_id}")
        if old_pos != u.position_id:
            changed.append(f"岗位 {old_pos}→{u.position_id}")
        if old_jl != u.job_level_id:
            changed.append(f"职级 {old_jl}→{u.job_level_id}")
        EmployeeChangeLog.objects.create(
            user=u, action="TRANSFER", operator=instance.approver,
            field="department/position/job_level",
            old_value=f"dept={old_dept},pos={old_pos},jl={old_jl}",
            new_value=f"dept={u.department_id},pos={u.position_id},jl={u.job_level_id}",
            remark="调岗/调级审批通过，自动同步通讯录" + ("；".join(changed) if changed else ""))


# ---------- 离职通过：置已离职 ----------
@receiver(post_save, sender=ResignApplication)
def _resign_approved(sender, instance, created, **kwargs):
    if instance.status == "APPROVED" and getattr(instance, "_old_status", None) != "APPROVED":
        u = instance.user
        if u and u.status != "RESIGNED":
            u.status = "RESIGNED"
            u.leave_date = instance.resign_date or timezone.localdate()
            u.is_active = False
            u.save(update_fields=["status", "leave_date", "is_active"])
            EmployeeChangeLog.objects.create(
                user=u, action="RESIGN", operator=instance.approver,
                field="status", old_value="在职", new_value="已离职",
                remark=f"离职审批通过；原因：{instance.reason_type or '未填写'}；交接人：{instance.handover_to.display_name if instance.handover_to else '无'}")


# ---------- 请假通过：回写假期余额 ----------
@receiver(post_save, sender=LeaveApplication)
def _leave_approved_update_balance(sender, instance, created, **kwargs):
    if instance.status != "APPROVED":
        return
    if getattr(instance, "_leave_synced", False):
        return
    field_map = {"ANNUAL": "annual_used", "OFF": "compensate_used", "PERSONAL": "personal_used"}
    flag = field_map.get(instance.leave_type)
    if not flag:
        instance._leave_synced = True
        return
    year = (instance.start_at or timezone.now()).year
    balance, _ = LeaveBalance.objects.get_or_create(user=instance.user, year=year)
    setattr(balance, flag, (getattr(balance, flag) or 0) + (instance.days or 0))
    balance.save()
    instance._leave_synced = True


# ---------- 审批结果订阅消息推送（2026-10-02 增量，纯新增）----------
# 说明：
# - 一次性订阅消息**不需要微信认证**；未配置小程序凭证时 apps.common.wechat 静默跳过，
#   不影响上面的假期余额回写等任何既有逻辑；
# - 只在状态「变为」APPROVED/REJECTED 时推一次（靠 _old_status 与 _wx_pushed 双重防重）。
def _push_approval_result(instance, biz_name, page):
    status = getattr(instance, "status", "")
    if status not in ("APPROVED", "REJECTED"):
        return
    if getattr(instance, "_wx_pushed", False):
        return
    if getattr(instance, "_old_status", None) == status:
        return
    user = getattr(instance, "user", None)
    if not user:
        return
    from apps.common import wechat
    wechat.push_approval_result(
        user,
        biz_name,
        approved=(status == "APPROVED"),
        remark=getattr(instance, "approve_remark", "") or "",
        page=page,
    )
    instance._wx_pushed = True


@receiver(post_save, sender=LeaveApplication)
def _leave_result_push(sender, instance, created, **kwargs):
    _push_approval_result(instance, "请假申请", "pages/hr/leave")


@receiver(post_save, sender=ExpenseApplication)
def _expense_result_push(sender, instance, created, **kwargs):
    _push_approval_result(instance, "报销申请", "pages/hr/expense")
