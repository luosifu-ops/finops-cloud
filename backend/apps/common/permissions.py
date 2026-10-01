"""角色权限与数据范围"""
from rest_framework.permissions import BasePermission


def visible_user_ids(user):
    """按角色返回可见的员工 ID 集合
    BOSS/HR -> 全部；MANAGER -> 本部门；LEADER -> 本小组；EMPLOYEE -> 自己
    """
    from apps.accounts.models import User

    if user.is_superuser or user.role in ("BOSS", "HR"):
        return User.objects.values_list("id", flat=True)
    if user.role == "MANAGER":
        if user.department_id:
            return User.objects.filter(department_id=user.department_id).values_list("id", flat=True)
        return User.objects.filter(id=user.id).values_list("id", flat=True)
    if user.role == "LEADER":
        if user.team_id:
            return User.objects.filter(team_id=user.team_id).values_list("id", flat=True)
        if user.department_id:
            return User.objects.filter(department_id=user.department_id).values_list("id", flat=True)
        return User.objects.filter(id=user.id).values_list("id", flat=True)
    return User.objects.filter(id=user.id).values_list("id", flat=True)


class IsBoss(BasePermission):
    """仅老板/超管"""
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.is_superuser or u.role == "BOSS"))


class IsManagerOrAbove(BasePermission):
    """部门经理及以上"""
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.is_superuser or u.role in ("BOSS", "MANAGER")))


class IsLeaderOrAbove(BasePermission):
    """组长及以上（可查看团队数据）"""
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.is_superuser or u.role in ("BOSS", "MANAGER", "LEADER")))


class IsHR(BasePermission):
    """人事或老板"""
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.is_superuser or u.role in ("BOSS", "HR")))
