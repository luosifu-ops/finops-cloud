"""通用 ViewSet：自动处理数据范围、创建人、软删除 + 全局操作日志/时间筛选/批量删除

2026-10-29 权限隔离专项改造要点：
1. 新增 scope_profile：'hr' 人事口径（BOSS+HR 全量）/ 'biz' 业务口径（仅 BOSS 全量）
2. 新增 scope_fields：支持多归属字段 OR 与链式路径（如 task__accountant）
3. owner 路径自动校验：配置的字段不存在时自动降级到 created_by/不做收窄，
   彻底消除「模型没有 user 字段 → 非老板账号访问 500」的隐患
4. perform_create：所有角色在归属为空时都回填本人，避免主管建的数据下属看不到
"""
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .permissions import visible_user_ids, biz_user_ids, is_boss, is_hr_scope
from .services import log_action


def _model_has_path(model, path):
    """校验 a__b__c 这样的字段路径在模型上是否真实存在"""
    if not path:
        return False
    cur = model
    for part in str(path).split("__"):
        if cur is None:
            return False
        try:
            field = cur._meta.get_field(part)
        except Exception:
            return False
        cur = field.related_model if field.is_relation else None
    return True


class ScopeModelViewSet(viewsets.ModelViewSet):
    """按角色自动收窄数据范围。

    子类可配置：
        owner_field = "user"        # 数据归属字段名，默认 user
        scope_fields = ()           # 多归属字段（OR 关系，支持链式），配置后优先于 owner_field
        scope_profile = "hr"        # "hr" 人事口径(BOSS+HR全量) | "biz" 业务口径(仅BOSS全量)
        scope_by_department = False # True 时主管按部门过滤（而非仅本人/小组）
        log_module = "销售线索"      # 操作日志中的模块名（建议配置）
        date_field = "created_at"   # 时间范围筛选字段
    """
    owner_field = "user"
    scope_fields = ()
    scope_profile = "hr"
    scope_by_department = False
    log_module = ""
    date_field = "created_at"

    # ---------- 内部工具 ----------
    def _scope_paths(self):
        """返回真正可用的归属字段路径元组"""
        model = self.get_queryset_model()
        candidates = [p for p in (self.scope_fields or ()) if p]
        if not candidates and self.owner_field:
            candidates = [self.owner_field]
        valid = tuple(p for p in candidates if _model_has_path(model, p))
        if valid:
            return valid
        # 兜底：任何 BaseModel 都有 created_by
        if _model_has_path(model, "created_by"):
            return ("created_by",)
        return ()

    def get_queryset_model(self):
        qs = getattr(self, "queryset", None)
        if qs is not None:
            return qs.model
        return self.get_serializer_class().Meta.model

    def _scoped_qs(self, qs, user):
        """按当前账号角色返回收窄后的 queryset"""
        if self.scope_profile == "biz":
            see_all = is_boss(user)
            ids_fn = biz_user_ids
        else:
            see_all = is_hr_scope(user)
            ids_fn = visible_user_ids
        if see_all:
            return qs

        paths = self._scope_paths()
        if not paths:
            return qs  # 模型没有归属字段（字典/配置类），不做收窄

        # 部门主管：按归属人所在部门过滤（比逐个 id 更稳，能覆盖 null 归属之外的场景）
        if user.role == "MANAGER" and self.scope_by_department and user.department_id:
            cond = Q()
            for p in paths:
                cond |= Q(**{f"{p}__department_id": user.department_id})
            return qs.filter(cond)

        ids = ids_fn(user)
        cond = Q()
        for p in paths:
            cond |= Q(**{f"{p}__in": ids})
        return qs.filter(cond)

    # ---------- 查询 ----------
    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user or not user.is_authenticated:
            return qs.none()
        base = self._scoped_qs(qs, user)
        # 主管分配出去的内容，分配人(assigned_by)保留可见+可编辑权限
        model = qs.model
        if hasattr(model, "assigned_by"):
            base = base | qs.filter(assigned_by=user)
        qs = base.distinct()
        # 全局规则1：时间范围筛选（start_date / end_date，含当天）
        p = self.request.query_params
        start, end = p.get("start_date"), p.get("end_date")
        if start or end:
            f = self.date_field
            if hasattr(model, f):
                if start:
                    qs = qs.filter(**{f + "__gte": start})
                if end:
                    qs = qs.filter(**{f + "__lte": end + " 23:59:59"} if len(end) <= 10 else {f + "__lte": end})
        return qs

    # ---------- 写入 ----------
    def perform_create(self, serializer):
        kwargs = {}
        model = serializer.Meta.model
        if hasattr(model, "created_by"):
            kwargs["created_by"] = self.request.user
        # 归属字段为空时一律回填当前用户：
        # 原来只对 EMPLOYEE 回填，导致主管/组长建的单据没有归属人，
        # 本部门下属看不到、部门筛选也捞不到 —— 本次修正
        for path in self._scope_paths():
            if "__" in path:
                continue
            head = path.split("__")[0]
            try:
                field = model._meta.get_field(head)
            except Exception:
                continue
            if not field.is_relation or not getattr(field, "null", False):
                continue
            if head in serializer.validated_data:
                continue
            kwargs[head] = self.request.user
        inst = serializer.save(**kwargs)
        log_action(self.request, "CREATE", module=self.log_module, obj=inst)

    def perform_update(self, serializer):
        inst = serializer.save()
        changed = list(serializer.validated_data.keys())
        log_action(self.request, "UPDATE", module=self.log_module, obj=inst,
                   detail="修改字段: " + ",".join(map(str, changed))[:500] if changed else "")

    def perform_destroy(self, instance):
        log_action(self.request, "DELETE", module=self.log_module, obj=instance)
        if hasattr(instance, "soft_delete"):
            instance.soft_delete()
        else:
            instance.delete()

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """简易计数统计，子类可覆写"""
        return Response({"count": self.get_queryset().count()})

    @action(detail=False, methods=["post"], url_path="bulk-delete")
    def bulk_delete(self, request):
        """全局规则1：批量删除。body: {"ids": [..]}，走软删除并写日志"""
        ids = request.data.get("ids") or []
        if not isinstance(ids, list) or not ids:
            return Response({"code": 1, "msg": "请传入要删除的 ids 数组"}, status=status.HTTP_400_BAD_REQUEST)
        qs = self.filter_queryset(self.get_queryset()).filter(id__in=ids)
        n = 0
        for inst in qs:
            log_action(request, "BULK_DELETE", module=self.log_module, obj=inst)
            if hasattr(inst, "soft_delete"):
                inst.soft_delete()
            else:
                inst.delete()
            n += 1
        return Response({"code": 0, "msg": f"已删除 {n} 条", "deleted": n})

    @action(detail=False, methods=["get"], url_path="export")
    def export_all(self, request):
        """全局规则1：导出当前筛选下的全量数据（JSON），前端转 CSV/Excel"""
        serializer_class = self.get_serializer_class()
        rows = serializer_class(self.filter_queryset(self.get_queryset()), many=True).data
        log_action(request, "EXPORT", module=self.log_module, detail=f"导出 {len(rows)} 条")
        return Response({"code": 0, "data": rows, "total": len(rows)})


class BizScopeModelViewSet(ScopeModelViewSet):
    """经营数据专用基类：只有老板/总经理看全公司，其余账号按部门/小组/本人收窄。

    用于客户、合同、线索、业绩、凭证、发票、投放等业务数据。
    """
    scope_profile = "biz"
