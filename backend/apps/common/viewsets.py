"""通用 ViewSet：自动处理数据范围、创建人、软删除"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .permissions import visible_user_ids


class ScopeModelViewSet(viewsets.ModelViewSet):
    """按角色自动收窄数据范围。

    子类可配置：
        owner_field = "user"        # 数据归属字段名，默认 user
        scope_by_department = False # True 时主管按部门过滤（而非仅本人/小组）
    """
    owner_field = "user"
    scope_by_department = False

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user or not user.is_authenticated:
            return qs.none()
        if user.is_superuser or user.role in ("BOSS", "HR"):
            return qs
        if user.role == "MANAGER" and self.scope_by_department and user.department_id:
            base = qs.filter(**{f"{self.owner_field}__department_id": user.department_id})
        else:
            ids = visible_user_ids(user)
            base = qs.filter(**{f"{self.owner_field}__in": ids})
        # 增量功能（阶段三）：主管分配出去的内容，分配人(assigned_by)保留可见+可编辑权限。
        # 仅当模型含 assigned_by 字段时生效；与原有 owner 隔离逻辑互不冲突。
        model = qs.model
        if hasattr(model, "assigned_by"):
            base = base | qs.filter(assigned_by=user)
        return base.distinct()

    def perform_create(self, serializer):
        kwargs = {}
        if hasattr(serializer.Meta.model, "created_by"):
            kwargs["created_by"] = self.request.user
        model = serializer.Meta.model
        # 若模型有 owner 字段且未显式传入，默认当前用户
        if self.owner_field and hasattr(model, self.owner_field):
            field = getattr(model, self.owner_field).field
            if field.null and self.owner_field not in serializer.validated_data:
                if self.request.user.role == "EMPLOYEE":
                    kwargs[self.owner_field] = self.request.user
        serializer.save(**kwargs)

    def perform_destroy(self, instance):
        if hasattr(instance, "soft_delete"):
            instance.soft_delete()
        else:
            instance.delete()

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """简易计数统计，子类可覆写"""
        return Response({"count": self.get_queryset().count()})
