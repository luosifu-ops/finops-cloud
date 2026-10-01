"""合同订单名录：权限与数据范围（电销部 / 运营部 独立核算）

规则：
  - 老板 / 管理层（BOSS / MANAGER）→ 查看全部合同
  - 电销部员工 → 仅看「电销部」合同
  - 运营部员工 → 仅看「运营部」合同
  - 其他人员 → 仅看自己签的单
"""
from django.db.models import Q
from rest_framework.permissions import BasePermission


def is_manager(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return getattr(user, "role", None) in ("BOSS", "MANAGER")


def dept_code(user):
    if not getattr(user, "department_id", None):
        return None
    return getattr(user.department, "code", None) if user.department else None


def scope_contracts(qs, user):
    """按权限过滤合同查询集"""
    if is_manager(user):
        return qs
    code = dept_code(user)
    if code == "SALES":
        return qs.filter(dept="SALES")
    if code == "OPS":
        return qs.filter(dept="OPS")
    # 其他：仅自己签单
    return qs.filter(signer=user)


class IsContractManager(BasePermission):
    """合同管理（查看全部 / 审核）权限：老板或管理层"""

    def has_permission(self, request, view):
        return is_manager(request.user)
