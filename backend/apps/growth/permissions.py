"""增长中心：权限与数据范围

【不改动 apps.common.permissions】本文件独立实现增长中心的三层可见性：
  1. 超级总账号（超管 / BOSS / HR / 角色开启 can_view_all）→ 查看全公司所有线索与进度
  2. 运营 → 仅查看「自己录入」线索的承接进度
  3. 成交师 → 仅查看「分配给自己」的线索 + 公海待领取
  4. 同级员工默认互相不可见（仅能看到与自己相关的记录）
"""
from django.db.models import Q
from rest_framework.permissions import BasePermission


def growth_role_of(user):
    """取用户在增长中心的职能角色（GrowthRole），没有则返回 None"""
    if not user or not user.is_authenticated:
        return None
    try:
        return user.growth_role
    except Exception:
        return None


def _dept_user_ids(user):
    """按部门/团队返回可见用户 ID 集合（用于部门维度隔离）

    MANAGER → 本部门全员；LEADER → 本组（无组则本部门）；其余返回 None 表示不适用。
    """
    from apps.accounts.models import User

    role = getattr(user, "role", None)
    if role == "MANAGER" and getattr(user, "department_id", None):
        return list(User.objects.filter(
            department_id=user.department_id).values_list("id", flat=True))
    if role == "LEADER":
        if getattr(user, "team_id", None):
            return list(User.objects.filter(
                team_id=user.team_id).values_list("id", flat=True))
        if getattr(user, "department_id", None):
            return list(User.objects.filter(
                department_id=user.department_id).values_list("id", flat=True))
    return None


def can_view_all(user):
    """可查看全公司所有线索 / 所有对接人 / 所有进度

    【Boss 2026-09-07 指示】权限按部门划分，**只有管理层（MANAGER）和老板（BOSS）
    才可以看到所有数据**。HR 不再默认拥有全量权限；如需对个别账号开放，
    可通过 GrowthRole.can_view_all 显式授权。
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if getattr(user, "role", None) in ("BOSS", "MANAGER"):
        return True
    r = growth_role_of(user)
    return bool(r and r.can_view_all)


def is_ops(user):
    r = growth_role_of(user)
    return bool(r and r.role == "OPS")


def is_closer(user):
    r = growth_role_of(user)
    return bool(r and r.role == "CLOSER")


def is_field(user):
    r = growth_role_of(user)
    return bool(r and r.role == "FIELD")


def is_field_manager(user):
    """外勤主管：可查看全部外勤任务并派单

    - 超管 / BOSS / 管理层（can_view_all）天然拥有
    - 或 GrowthRole 角色为 FIELD 且开启了 can_view_all
    - 或用户在组织内为经理/主管（role=MANAGER/LEADER）
    """
    if can_view_all(user):
        return True
    r = growth_role_of(user)
    if r and r.role == "FIELD" and r.can_view_all:
        return True
    return getattr(user, "role", None) in ("MANAGER", "LEADER")


def scope_leads(qs, user):
    """按权限过滤线索扩展（LeadExt）查询集

    优先级：全量（老板/管理层）> 部门维度（经理/组长）> 职能角色（运营/成交师）> 个人
    """
    if can_view_all(user):
        return qs

    # 1) 部门 / 团队维度
    ids = _dept_user_ids(user)
    if ids is not None:
        return qs.filter(Q(ops_owner_id__in=ids) | Q(closer_id__in=ids)).distinct()

    # 2) 职能角色
    r = growth_role_of(user)
    role = r.role if r else None
    if role == "OPS":
        # 运营本人：仅自己录入的线索（可看承接进度）
        return qs.filter(ops_owner=user).distinct()
    if role == "CLOSER":
        # 成交师：分配给自己的 + 公海待领取（可主动领取）
        # 注意：平台专项只决定「派给谁」，不扩大可见范围 ——
        #      同级成交师之间互相看不到对方的单，只能看到公海
        return qs.filter(Q(closer=user) | Q(in_pool=True)).distinct()
    if role == "FIELD":
        # 外勤不参与线索池
        return qs.none()

    # 3) 其他：仅与自己相关（录入或承接）
    return (qs.filter(ops_owner=user) | qs.filter(closer=user)).distinct()


def scope_field_tasks(qs, user):
    """外勤任务可见范围

    - 超级总账号：全部
    - 外勤人员：分配给自己的 + 待接收池（status=PENDING 且未分配），可主动接单打通
    - 销售（创建人）：自己下单的任务（可自主查看外勤进度，无需询问）
    - 其他：无
    """
    if can_view_all(user):
        return qs
    if is_field(user):
        # 外勤：已分配自己的 + 待接收池（可主动接单），实现「电销/运营 → 外勤」流程打通
        return (qs.filter(assignee=user) | qs.filter(status="PENDING", assignee__isnull=True)).distinct()
    return (qs.filter(assignee=user) | qs.filter(creator=user)).distinct()


def scope_projects(qs, user):
    """增值业务部项目可见范围"""
    if can_view_all(user):
        return qs
    r = growth_role_of(user)
    if r and r.dept_key == "VALUE_ADDED":
        # 增值业务部内部：主管看全部本部门，专员看自己的
        if r.role == "VA_MANAGER":
            return qs
        return qs.filter(owner=user).distinct()
    return qs.filter(owner=user).distinct()


class IsGrowthAdmin(BasePermission):
    """增长中心管理员：超管 / BOSS / HR，或角色开启 can_view_all"""

    def has_permission(self, request, view):
        return can_view_all(request.user)


class IsOpsOrAdmin(BasePermission):
    """运营或管理员（线索录入权限）"""

    def has_permission(self, request, view):
        u = request.user
        return can_view_all(u) or is_ops(u)


class IsCloserOrAdmin(BasePermission):
    """成交师或管理员（承接线索权限）"""

    def has_permission(self, request, view):
        u = request.user
        return can_view_all(u) or is_closer(u)


class IsFieldOrAdmin(BasePermission):
    """外勤人员或管理员（接单与进度上报权限）"""

    def has_permission(self, request, view):
        u = request.user
        return can_view_all(u) or is_field(u)


class IsFieldManagerOrAdmin(BasePermission):
    """外勤主管或管理员（查看全部外勤任务 + 派单权限）"""

    def has_permission(self, request, view):
        return is_field_manager(request.user)
