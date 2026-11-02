"""角色权限与数据范围

2026-10-29 权限隔离专项（Boss 需求）：
    普通员工   —— 只看自己的数据；可访问全部公共功能；看不到其他部门任何人的数据
    部门主管   —— 只看本部门全部员工数据；可访问全部公共功能；看不到其他部门数据
    老板/总经理 —— 全部数据、全部功能，无隔离

本文件提供两套口径（重要，勿混用）：
    visible_user_ids(user)  「人事口径」：BOSS + HR 都能看全员
                             用于员工档案、考勤、薪酬、审批、劳动合同等人事数据
    biz_user_ids(user)      「业务口径」：只有老板/总经理看全公司
                             用于客户、合同、线索、业绩、凭证、发票、投放等经营数据
                             HR 不再自动获得全公司业务数据
"""
from rest_framework.permissions import BasePermission

# 老板/总经理（唯一不做数据隔离的角色）
BOSS_ROLES = ("BOSS",)
# 人事职能（可见全公司人事档案，但不可见全公司经营数据）
HR_ROLES = ("BOSS", "HR")


def is_authenticated_user(user):
    return bool(user and getattr(user, "is_authenticated", False))


def is_boss(user):
    """是否老板/总经理（含超级管理员）。仅这类账号不做数据隔离。"""
    return bool(is_authenticated_user(user) and (user.is_superuser or user.role in BOSS_ROLES))


def is_hr_scope(user):
    """是否人事口径的全量账号（BOSS 或 HR）"""
    return bool(is_authenticated_user(user) and (user.is_superuser or user.role in HR_ROLES))


def _own_ids(user):
    from apps.accounts.models import User
    return User.objects.filter(id=user.id).values_list("id", flat=True)


def _dept_scoped_ids(user):
    """按「部门主管 → 本部门 / 组长 → 本小组 / 其他 → 本人」收窄"""
    from apps.accounts.models import User

    if user.role == "MANAGER" and user.department_id:
        return User.objects.filter(department_id=user.department_id).values_list("id", flat=True)
    if user.role == "LEADER":
        if user.team_id:
            return User.objects.filter(team_id=user.team_id).values_list("id", flat=True)
        if user.department_id:
            return User.objects.filter(department_id=user.department_id).values_list("id", flat=True)
    return _own_ids(user)


def visible_user_ids(user):
    """人事口径可见员工集合：BOSS/HR → 全部；MANAGER → 本部门；LEADER → 本小组；EMPLOYEE → 自己"""
    from apps.accounts.models import User

    if not is_authenticated_user(user):
        return User.objects.none().values_list("id", flat=True)
    if is_hr_scope(user):
        return User.objects.values_list("id", flat=True)
    return _dept_scoped_ids(user)


def biz_user_ids(user):
    """业务口径可见员工集合：仅 BOSS/总经理 → 全部；其余（含 HR）→ 部门/小组/本人"""
    from apps.accounts.models import User

    if not is_authenticated_user(user):
        return User.objects.none().values_list("id", flat=True)
    if is_boss(user):
        return User.objects.values_list("id", flat=True)
    return _dept_scoped_ids(user)


def department_heads(department_id):
    """某部门的负责人账号（主管/经理/组长），用于汇报自动流转与业绩汇总"""
    from apps.accounts.models import User

    if not department_id:
        return User.objects.none()
    return User.objects.filter(
        department_id=department_id, role__in=("MANAGER", "LEADER"), is_active=True
    )


def department_head_ids(department_id):
    return list(department_heads(department_id).values_list("id", flat=True))


def report_receivers(user):
    """一份汇报提交后应该流转到的接收人：
    1) 直属部门的主管/经理
    2) 若本部门无主管，则升级到老板/总经理
    3) 组长自己的汇报不再回推给自己
    """
    from apps.accounts.models import User

    receivers = list(department_heads(getattr(user, "department_id", None)).exclude(id=user.id))
    if receivers:
        return receivers
    bosses = list(User.objects.filter(role__in=BOSS_ROLES, is_active=True).exclude(id=user.id))
    return bosses


class IsBoss(BasePermission):
    """仅老板/超管"""
    def has_permission(self, request, view):
        return is_boss(request.user)


class IsManagerOrAbove(BasePermission):
    """部门经理及以上"""
    def has_permission(self, request, view):
        u = request.user
        return bool(is_authenticated_user(u) and (u.is_superuser or u.role in ("BOSS", "MANAGER")))


class IsLeaderOrAbove(BasePermission):
    """组长及以上（可查看团队数据）"""
    def has_permission(self, request, view):
        u = request.user
        return bool(is_authenticated_user(u) and (u.is_superuser or u.role in ("BOSS", "MANAGER", "LEADER")))


class IsHR(BasePermission):
    """人事或老板"""
    def has_permission(self, request, view):
        return is_hr_scope(request.user)
