"""增长中心：视图集（纯新增）

业务闭环：
  运营录入线索 → 自动流转成交师 → 成交师承接 →（无法跟进）退回公海 → 二次领取
  → 承接后下发外勤/增值任务 → 外勤实时上报进度 → 销售可视全程进度

【零改动原则】仅向 sales.Lead 新增记录，不修改其结构与任何既有逻辑。
"""
from datetime import date

from django.db import transaction
from django.db.models import Q, Count, Sum
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.sales.models import Lead
from .models import (
    LeadChannel, LeadExt, LeadFlow, LeadPool, LeadStageLog,
    FieldTask, FieldProgress, ValueAddedProject, AdSpendRecord, GrowthRole,
    CloserChannel, LeadFollowUp, FieldTaskNode,
)
from .serializers import (
    LeadChannelSerializer, LeadExtSerializer, LeadExtCreateSerializer,
    LeadFlowSerializer, LeadPoolSerializer, LeadStageLogSerializer,
    FieldTaskSerializer, FieldProgressSerializer,
    ValueAddedProjectSerializer, AdSpendRecordSerializer, GrowthRoleSerializer,
    CloserChannelSerializer, LeadFollowUpSerializer, FieldTaskNodeSerializer,
)
from .permissions import (
    can_view_all, is_ops, scope_leads, scope_field_tasks, scope_projects,
    IsGrowthAdmin, IsOpsOrAdmin, IsCloserOrAdmin, IsFieldOrAdmin,
    IsFieldManagerOrAdmin, is_field_manager,
)

# 旧 Lead.SOURCE 的合法枚举（新平台落 OTHER，保证旧模块不受影响）
LEGACY_SOURCE = {
    "AMAP", "BAIDU", "XIAOHONGSHU", "DOUYIN", "KUAISHOU",
    "WECHAT", "REFERRAL", "OFFLINE", "OTHER",
}


def _legacy_source(code):
    """把新渠道编码映射到旧 Lead.source；未知平台统一 OTHER"""
    return code if code in LEGACY_SOURCE else "OTHER"


def _auto_pick_closer(channel=None):
    """按平台专项分配成交师

    派单优先级：
      1. 该平台有专项绑定（CloserChannel 且启用）→ 在其中按「在手负载最少」分配，
         负载相同时 priority 高者优先
      2. 该平台无专项绑定 → 降级到全部成交师按负载分配
      3. 无任何成交师 → 返回 None（线索自动进入公海）
    """
    from .models import CloserChannel

    candidates = []          # [(load, -priority, user)]
    if channel is not None:
        bindings = CloserChannel.objects.filter(
            channel=channel, is_active=True, is_deleted=False
        ).select_related("user")
        for b in bindings:
            load = LeadExt.objects.filter(
                closer=b.user, is_deleted=False, in_pool=False).count()
            candidates.append((load, -(b.priority or 0), b.user))

    if not candidates:
        # 降级：全平台成交师按负载
        for r in GrowthRole.objects.filter(
                role="CLOSER", is_deleted=False).select_related("user"):
            load = LeadExt.objects.filter(
                closer=r.user, is_deleted=False, in_pool=False).count()
            candidates.append((load, 0, r.user))

    if not candidates:
        return None

    candidates.sort(key=lambda x: (x[0], x[1]))
    return candidates[0][2]


# ---------------- 渠道字典 ----------------
class LeadChannelViewSet(viewsets.ModelViewSet):
    """投放渠道（含预留扩展位，可后台开关）"""
    queryset = LeadChannel.objects.filter(is_deleted=False)
    serializer_class = LeadChannelSerializer
    search_fields = ["code", "name"]
    ordering_fields = ["sort", "id"]

    def get_queryset(self):
        qs = super().get_queryset()
        # 默认只返回已启用渠道；加 ?all=1 查看全部（含预留位）
        if self.request.query_params.get("all") != "1":
            qs = qs.filter(is_enabled=True)
        return qs.order_by("sort", "id")

    @action(detail=True, methods=["post"], permission_classes=[IsGrowthAdmin])
    def toggle(self, request, pk=None):
        """启用/停用渠道（预留平台一键开启）"""
        ch = self.get_object()
        ch.is_enabled = not ch.is_enabled
        ch.save(update_fields=["is_enabled"])
        return Response({"id": ch.id, "is_enabled": ch.is_enabled})


# ---------------- 线索录入与流转 ----------------
class LeadExtViewSet(viewsets.ModelViewSet):
    """多平台线索录入 + 全链路流转 + 权限隔离"""
    queryset = LeadExt.objects.filter(is_deleted=False).select_related(
        "lead", "channel", "ops_owner", "closer")
    serializer_class = LeadExtSerializer
    search_fields = ["source_account_no", "contact_value", "lead__name", "lead__phone"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = scope_leads(qs, self.request.user)   # 权限隔离
        p = self.request.query_params
        if p.get("channel"):
            qs = qs.filter(channel_id=p["channel"])
        if p.get("stage"):
            qs = qs.filter(stage_3570=p["stage"])
        if p.get("in_pool") in ("1", "true", "True"):
            qs = qs.filter(in_pool=True)
        if p.get("closer"):
            qs = qs.filter(closer_id=p["closer"])
        return qs.order_by("-created_at")

    # ---------- 录入（运营） ----------
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """运营录入线索 → 自动流转至成交师

        必填：来源平台 / 来源账号编号 / 客户联系方式 / 归属运营人（自动=当前登录人）
        """
        ser = LeadExtCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        user = request.user

        channel = d["channel"]
        # 录入权限：仅运营角色（或老板/管理层/显式授权者）可录入
        if not (can_view_all(user) or is_ops(user)):
            return Response(
                {"detail": "仅运营角色可录入线索（如需权限请联系管理员配置）"},
                status=status.HTTP_403_FORBIDDEN)
        closer_id = d.get("closer")
        closer = None
        if closer_id:
            from apps.accounts.models import User
            closer = User.objects.filter(id=closer_id).first()
        if closer is None:
            closer = _auto_pick_closer(channel)   # 按平台专项分配

        # 1) 在原 Lead 表新增一条记录（不改动 Lead 任何结构）
        lead = Lead.objects.create(
            name=d["name"],
            phone=d.get("phone") or "",
            wechat=d.get("wechat") or "",
            company=d.get("company") or "",
            intention=d.get("intention") or "",
            source=_legacy_source(channel.code),
            source_detail=f"{channel.name}/{d['source_account_no']}",
            status="ASSIGNED" if closer else "NEW",
            owner=None,
            remark=d.get("remark") or "",
            assigned_at=timezone.now() if closer else None,
            created_by=user,
        )
        # 2) 扩展信息
        ext = LeadExt.objects.create(
            lead=lead, channel=channel,
            source_account_no=d["source_account_no"],
            contact_type=d["contact_type"],
            contact_value=d.get("contact_value") or (d.get("phone") or d.get("wechat") or ""),
            ops_owner=user,
            closer=closer,
            in_pool=(closer is None),
            customer_need=d.get("customer_need") or "",
            contact_person=d.get("contact_person") or "",
            acquisition_cost=d.get("acquisition_cost") or 0,
            deal_amount=d.get("deal_amount") or 0,
            created_by=user,
        )
        # 3) 流转留痕
        LeadFlow.objects.create(
            lead_ext=ext, action="SUBMIT", from_user=user,
            remark="运营录入", created_by=user)
        if closer:
            LeadFlow.objects.create(
                lead_ext=ext, action="AUTO_ASSIGN", from_user=user, to_user=closer,
                remark="系统自动流转（按负载）", created_by=user)
        else:
            LeadPool.objects.create(
                lead_ext=ext, status="WAITING",
                returned_reason="无可用成交师，自动进入公海", created_by=user)

        return Response(LeadExtSerializer(ext).data, status=status.HTTP_201_CREATED)

    # ---------- 成交师承接 ----------
    @action(detail=True, methods=["post"], permission_classes=[IsCloserOrAdmin])
    def accept(self, request, pk=None):
        """成交师承接线索"""
        ext = self.get_object()
        ext.closer = request.user
        ext.in_pool = False
        ext.save(update_fields=["closer", "in_pool"])
        LeadFlow.objects.create(
            lead_ext=ext, action="ACCEPT", to_user=request.user,
            remark=request.data.get("remark") or "", created_by=request.user)
        # 关掉公海记录
        LeadPool.objects.filter(lead_ext=ext, status="WAITING").update(status="CLAIMED")
        return Response({"detail": "已承接", "id": ext.id})

    # ---------- 退回公海 ----------
    @action(detail=True, methods=["post"], permission_classes=[IsCloserOrAdmin])
    def return_pool(self, request, pk=None):
        """承接人无法跟进 → 退回公海，支持二次分配"""
        ext = self.get_object()
        reason = request.data.get("reason") or "无法跟进"
        with transaction.atomic():
            ext.closer = None
            ext.in_pool = True
            ext.save(update_fields=["closer", "in_pool"])
            LeadFlow.objects.create(
                lead_ext=ext, action="RETURN_POOL", from_user=request.user,
                remark=reason, created_by=request.user)
            pool, created = LeadPool.objects.get_or_create(
                lead_ext=ext, defaults={"created_by": request.user})
            pool.status = "WAITING"
            pool.returned_by = request.user
            pool.returned_reason = reason
            pool.returned_at = timezone.now()
            pool.claimed_by = None
            pool.claimed_at = None
            pool.save()
        return Response({"detail": "已退回公海", "id": ext.id})

    # ---------- 公海领取 ----------
    @action(detail=True, methods=["post"], permission_classes=[IsCloserOrAdmin])
    def claim(self, request, pk=None):
        """从公海二次领取线索"""
        ext = self.get_object()
        if not ext.in_pool:
            return Response({"detail": "该线索不在公海"}, status=status.HTTP_400_BAD_REQUEST)
        ext.closer = request.user
        ext.in_pool = False
        ext.save(update_fields=["closer", "in_pool"])
        LeadFlow.objects.create(
            lead_ext=ext, action="CLAIM", to_user=request.user,
            remark="公海领取", created_by=request.user)
        pool = getattr(ext, "pool", None)
        if pool:
            pool.status = "CLAIMED"
            pool.claimed_by = request.user
            pool.claimed_at = timezone.now()
            pool.claim_count = (pool.claim_count or 0) + 1
            pool.save()
        return Response({"detail": "已领取", "id": ext.id})

    # ---------- 转派 ----------
    @action(detail=True, methods=["post"], permission_classes=[IsGrowthAdmin])
    def transfer(self, request, pk=None):
        """管理员转派给其他成交师"""
        from apps.accounts.models import User
        ext = self.get_object()
        to_id = request.data.get("to_user")
        to_user = User.objects.filter(id=to_id).first()
        if not to_user:
            return Response({"detail": "目标用户不存在"}, status=status.HTTP_400_BAD_REQUEST)
        old = ext.closer
        ext.closer = to_user
        ext.in_pool = False
        ext.save(update_fields=["closer", "in_pool"])
        LeadFlow.objects.create(
            lead_ext=ext, action="TRANSFER", from_user=old or request.user, to_user=to_user,
            remark=request.data.get("remark") or "管理员转派", created_by=request.user)
        return Response({"detail": "已转派", "id": ext.id})

    # ---------- 管理层分配（手动指派运营/成交师） ----------
    @action(detail=True, methods=["post"], permission_classes=[IsGrowthAdmin])
    def assign(self, request, pk=None):
        """管理层手动分配线索给某运营 / 成交师（仅管理层 can_view_all 可调）

        请求体：
          owner_id  : 目标运营人 ID（改写 ops_owner，线索归其名下）
          closer_id : 目标成交师 ID（改写 closer，交由承接）
          remark    : 分配备注
        分配后线索移出公海（in_pool=False）并留痕（action=ASSIGN）。
        """
        from apps.accounts.models import User
        ext = self.get_object()
        owner_id = request.data.get("owner_id")
        closer_id = request.data.get("closer_id")
        remark = request.data.get("remark") or ""
        if owner_id is None and closer_id is None:
            return Response(
                {"detail": "请至少指定 owner_id（运营）或 closer_id（成交师）之一"},
                status=status.HTTP_400_BAD_REQUEST)
        # 先校验目标用户存在，避免事务内回滚麻烦
        owner = User.objects.filter(id=owner_id).first() if owner_id is not None else None
        closer = User.objects.filter(id=closer_id).first() if closer_id is not None else None
        if owner_id is not None and owner is None:
            return Response({"detail": f"运营人 ID {owner_id} 不存在"},
                            status=status.HTTP_400_BAD_REQUEST)
        if closer_id is not None and closer is None:
            return Response({"detail": f"成交师 ID {closer_id} 不存在"},
                            status=status.HTTP_400_BAD_REQUEST)
        old_owner = ext.ops_owner
        old_closer = ext.closer
        targets = []
        with transaction.atomic():
            if owner is not None:
                ext.ops_owner = owner
                targets.append(f"运营={getattr(owner, 'display_name', None) or owner.username}")
            if closer is not None:
                ext.closer = closer
                targets.append(f"成交师={getattr(closer, 'display_name', None) or closer.username}")
            ext.in_pool = False
            ext.save(update_fields=["ops_owner", "closer", "in_pool"])
            # 同步关闭公海待领取记录
            LeadPool.objects.filter(lead_ext=ext, status="WAITING").update(
                status="CLAIMED", claimed_by=request.user, claimed_at=timezone.now())
            LeadFlow.objects.create(
                lead_ext=ext, action="ASSIGN",
                from_user=(old_owner or old_closer or request.user),
                to_user=(ext.ops_owner or ext.closer or request.user),
                remark="管理层分配 → " + "；".join(targets) + (f"（{remark}）" if remark else ""),
                created_by=request.user)
        return Response({
            "detail": "已分配", "id": ext.id,
            "ops_owner": ext.ops_owner_id, "closer": ext.closer_id,
        })

    # ---------- 3570 阶段标记（人工） ----------
    @action(detail=True, methods=["post"])
    def set_stage(self, request, pk=None):
        """人工手动标记 3570 阶段（3/5/7 阶段，0 成交）"""
        ext = self.get_object()
        new_stage = request.data.get("stage")
        if new_stage not in dict(LeadExt.STAGE_3570):
            return Response({"detail": "阶段值非法"}, status=status.HTTP_400_BAD_REQUEST)
        old = ext.stage_3570
        ext.stage_3570 = new_stage
        ext.save(update_fields=["stage_3570"])
        LeadStageLog.objects.create(
            lead_ext=ext, old_stage=old or "", new_stage=new_stage,
            remark=request.data.get("remark") or "", created_by=request.user)
        # 标记 0 成交时，同步把原线索状态置为已成交（仅新增同步，不改旧逻辑）
        if new_stage == "S0" and ext.lead.status != "DEAL":
            ext.lead.status = "DEAL"
            ext.lead.dealt_at = timezone.now()
            ext.lead.save(update_fields=["status", "dealt_at"])
        return Response({"detail": "已标记", "stage": new_stage,
                         "stage_label": ext.get_stage_3570_display()})

    # ---------- 流转记录 ----------
    @action(detail=True, methods=["get"])
    def flows(self, request, pk=None):
        """查看单条线索的流转记录"""
        ext = self.get_object()
        qs = ext.flows.filter(is_deleted=False).order_by("-created_at")
        return Response(LeadFlowSerializer(qs, many=True).data)

    @action(detail=True, methods=["get"])
    def stage_logs(self, request, pk=None):
        """查看 3570 阶段变更历史"""
        ext = self.get_object()
        qs = ext.stage_logs.filter(is_deleted=False).order_by("-created_at")
        return Response(LeadStageLogSerializer(qs, many=True).data)

    # ---------- 穿透查看：点击运营/销售人员姓名，查看其全部平台/账号线索与转化 ----------
    @action(detail=False, methods=["get"])
    def by_person(self, request):
        """按人员穿透：返回该人负责的全部平台/账号线索明细 + 转化统计

        参数：?user_id=<运营或成交师ID>（不传则取当前登录人）
        权限：仅本人 / 管理员 / 部门主管可见
        """
        from apps.accounts.models import User

        uid = request.query_params.get("user_id")
        if uid:
            target = User.objects.filter(id=uid).first()
        else:
            target = request.user
        if not target:
            return Response({"detail": "用户不存在"}, status=status.HTTP_404_NOT_FOUND)

        # 权限：本人 / can_view_all / 同部门主管
        same_dept = (getattr(target, "department_id", None)
                     and target.department_id == getattr(request.user, "department_id", None))
        if not (can_view_all(request.user) or target == request.user
                or (same_dept and getattr(request.user, "role", None) in ("MANAGER", "LEADER"))):
            return Response({"detail": "无权查看该人员数据"}, status=status.HTTP_403_FORBIDDEN)

        qs = LeadExt.objects.filter(is_deleted=False).filter(
            Q(ops_owner=target) | Q(closer=target)
        ).select_related("lead", "channel")
        rows = LeadExtSerializer(qs.order_by("-created_at"), many=True).data

        # 按 平台+账号 聚合转化
        agg = {}
        for r in qs:
            key = f"{r.channel_id}::{r.source_account_no}"
            a = agg.setdefault(key, {
                "channel": r.channel.name, "channel_id": r.channel_id,
                "account": r.source_account_no, "total": 0, "deal": 0,
                "deal_amount": 0, "cost": 0,
            })
            a["total"] += 1
            if r.is_deal:
                a["deal"] += 1
            a["deal_amount"] += float(r.deal_amount or 0)
            a["cost"] += float(r.acquisition_cost or 0)
        for a in agg.values():
            a["rate"] = round(a["deal"] / a["total"] * 100, 2) if a["total"] else 0

        summary = {
            "user_id": target.id,
            "user_name": (getattr(target, "display_name", None) or target.get_full_name() or target.username),
            "total": qs.count(),
            "deal": sum(1 for r in qs if r.is_deal),
            "deal_amount": sum(float(r.deal_amount or 0) for r in qs),
            "cost": sum(float(r.acquisition_cost or 0) for r in qs),
            "by_account": list(agg.values()),
        }
        return Response({"summary": summary, "rows": rows})


# ---------------- 公共线索池（公海） ----------------
class LeadPoolViewSet(viewsets.ReadOnlyModelViewSet):
    """公共线索池：待领取 / 已领取"""
    queryset = LeadPool.objects.filter(is_deleted=False).select_related(
        "lead_ext", "lead_ext__lead", "lead_ext__channel")
    serializer_class = LeadPoolSerializer
    ordering_fields = ["created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        if not can_view_all(self.request.user):
            # 非管理员：公海待领取的对成交师可见
            qs = qs.filter(Q(status="WAITING") | Q(claimed_by=self.request.user))
        if self.request.query_params.get("status"):
            qs = qs.filter(status=self.request.query_params["status"])
        return qs.order_by("-created_at")


# ---------------- 流转记录 ----------------
class LeadFlowViewSet(viewsets.ReadOnlyModelViewSet):
    """线索流转记录（只读留痕）"""
    queryset = LeadFlow.objects.filter(is_deleted=False)
    serializer_class = LeadFlowSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if not can_view_all(self.request.user):
            qs = qs.filter(Q(from_user=self.request.user) | Q(to_user=self.request.user))
        if self.request.query_params.get("lead_ext"):
            qs = qs.filter(lead_ext_id=self.request.query_params["lead_ext"])
        return qs.order_by("-created_at").distinct()


# ---------------- 外勤（会计部下子模块） ----------------
def _create_field_task_nodes(task, user):
    """按业务类型预置模板生成结构化进度节点（资料确认 → 各环节 → 结果交付）"""
    codes = task.NODE_TEMPLATES.get(task.business_type, task.NODE_TEMPLATES["GENERAL"])
    for i, code in enumerate(codes):
        FieldTaskNode.objects.create(
            task=task, node=code, status="PENDING", order=i,
            created_by=user)


class FieldTaskViewSet(viewsets.ModelViewSet):
    """外勤任务：接收 / 办理 / 进度上报 / 销售端可视"""
    queryset = FieldTask.objects.filter(is_deleted=False).select_related("assignee", "creator")
    serializer_class = FieldTaskSerializer
    search_fields = ["title", "order_no", "customer_name"]
    ordering_fields = ["created_at", "due_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = scope_field_tasks(qs, self.request.user)   # 外勤看自己的，销售看自己下单的
        # 增量功能（阶段三）：主管派单给外勤后，派单人(assigned_by)保留可见+可编辑权限
        if self.request.user.is_authenticated:
            qs = qs | super().get_queryset().filter(assigned_by=self.request.user)
        p = self.request.query_params
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("order_no"):
            qs = qs.filter(order_no=p["order_no"])
        return qs.distinct().order_by("-created_at")

    def create(self, request, *args, **kwargs):
        # 销售下单：creator = 当前用户；下单后按业务类型自动生成节点模板
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(creator=request.user, created_by=request.user)
        task = serializer.instance
        _create_field_task_nodes(task, request.user)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=["post"], permission_classes=[IsFieldOrAdmin])
    def accept(self, request, pk=None):
        """外勤人员接收任务"""
        task = self.get_object()
        task.status = "ACCEPTED"
        task.accepted_at = timezone.now()
        if task.assignee is None:
            task.assignee = request.user
        task.save(update_fields=["status", "accepted_at", "assignee"])
        FieldProgress.objects.create(
            task=task, node="已接收", content=request.data.get("content") or "",
            reported_by=request.user, created_by=request.user)
        return Response({"detail": "已接收", "id": task.id})

    @action(detail=True, methods=["post"], permission_classes=[IsFieldOrAdmin])
    def report(self, request, pk=None):
        """外勤进度手动上报（每单可实时更新办理节点）"""
        task = self.get_object()
        node = request.data.get("node") or "进度更新"
        progress = FieldProgress.objects.create(
            task=task, node=node,
            content=request.data.get("content") or "",
            reported_by=request.user, created_by=request.user)
        # 同步任务状态
        new_status = request.data.get("status")
        if new_status in dict(FieldTask.STATUS):
            task.status = new_status
            if new_status == "DONE":
                task.finished_at = timezone.now()
            task.save(update_fields=["status", "finished_at"])
        return Response(FieldProgressSerializer(progress).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def progresses(self, request, pk=None):
        """查看进度流水（销售可自主查看，无需询问外勤）"""
        task = self.get_object()
        qs = task.progresses.filter(is_deleted=False).order_by("-created_at")
        return Response(FieldProgressSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], permission_classes=[IsFieldOrAdmin])
    def add_node(self, request, pk=None):
        """外勤在当前任务上点选添加一个预设节点"""
        task = self.get_object()
        node = request.data.get("node")
        if node not in dict(FieldTaskNode.NODES):
            return Response({"detail": "节点类型不存在"},
                            status=status.HTTP_400_BAD_REQUEST)
        order = task.nodes.filter(is_deleted=False).count()
        n = FieldTaskNode.objects.create(
            task=task, node=node, status="PENDING", order=order,
            created_by=request.user)
        return Response(FieldTaskNodeSerializer(n).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def node_choices(self, request):
        """所有可选的预设节点（供前端点选下拉）"""
        return Response([{"value": k, "label": v} for k, v in FieldTaskNode.NODES])

    # ---------- 外勤主管派单 ----------
    @action(detail=True, methods=["post"], permission_classes=[IsFieldManagerOrAdmin])
    def assign(self, request, pk=None):
        """外勤主管将任务分配给指定外勤人员（支持选择系统用户，或手动录入姓名）"""
        from apps.accounts.models import User
        from django.db.models import Q
        task = self.get_object()
        uid = request.data.get("assignee")
        name = (request.data.get("assignee_name") or "").strip()
        u = None
        if uid:
            u = User.objects.filter(id=uid).first()
        # 未提供有效用户 ID 时，尝试按录入的姓名匹配系统用户
        if u is None and name:
            u = (
                User.objects.filter(username=name).first()
                or User.objects.filter(first_name=name).first()
                or User.objects.filter(last_name=name).first()
            )
        if u is None and not name:
            return Response({"detail": "请选择或录入外勤人员"}, status=status.HTTP_400_BAD_REQUEST)
        if u:
            task.assignee = u
            task.assignee_name = u.display_name or u.username
        else:
            # 仅录入姓名且系统中无匹配用户：以自由文本留存
            task.assignee = None
            task.assignee_name = name
        task.assigned_by = request.user
        if task.status == "PENDING":
            task.status = "ACCEPTED"
            task.accepted_at = timezone.now()
        task.save(update_fields=["assignee", "assignee_name", "assigned_by", "status", "accepted_at"])
        FieldProgress.objects.create(
            task=task, node="主管派单", content=f"已派单给 {task.assignee_name}",
            reported_by=request.user, created_by=request.user)
        return Response({"detail": "已派单", "assignee_name": task.assignee_name})

    # ---------- 成交订单自动流转到外勤任务池 ----------
    @action(detail=False, methods=["post"], permission_classes=[IsGrowthAdmin])
    def from_deal(self, request):
        """电销/运营成交订单 → 自动生成外勤任务，进入外勤任务池等待派单

        请求体：{ customer_name, from_order_no, business_type?, task_type?, customer_type?, title? }
        """
        d = request.data
        customer_name = (d.get("customer_name") or "").strip()
        from_order_no = (d.get("from_order_no") or "").strip()
        if not customer_name and not from_order_no:
            return Response({"detail": "请至少提供客户名称或来源成交单号"},
                            status=status.HTTP_400_BAD_REQUEST)
        # 业务类型默认按 task_type 关键词推断，也可前端直接传
        task_type = (d.get("task_type") or "工商注册").strip()
        business_type = d.get("business_type") or ""
        if business_type not in dict(FieldTask.BUSINESS_TYPE):
            business_type = _infer_business_type(task_type)
        task = FieldTask.objects.create(
            title=d.get("title") or f"外勤办理-{customer_name or from_order_no}",
            customer_name=customer_name,
            customer_type=d.get("customer_type") or "ENTERPRISE",
            from_order_no=from_order_no,
            from_deal_id=d.get("from_deal_id"),
            business_type=business_type,
            task_type=task_type,
            status="PENDING",
            created_by=request.user,
        )
        _create_field_task_nodes(task, request.user)
        return Response(FieldTaskSerializer(task).data, status=status.HTTP_201_CREATED)


def _infer_business_type(task_type):
    """根据任务类型文本推断业务类型编码"""
    t = (task_type or "").strip()
    if "注销" in t:
        return "CANCEL"
    if "变更" in t or "执照变更" in t:
        return "CHANGE"
    if "地址异常" in t or "解异常" in t:
        return "ADDRESS_ABNORMAL"
    if "税务报到" in t or "税种核定" in t or "首次申报" in t:
        return "TAX_REGISTER"
    if "异常" in t:
        return "ABNORMAL"
    if "注册" in t:
        return "REGISTER"
    return "GENERAL"


class FieldProgressViewSet(viewsets.ModelViewSet):
    """外勤进度上报记录"""
    queryset = FieldProgress.objects.filter(is_deleted=False)
    serializer_class = FieldProgressSerializer

    def perform_create(self, serializer):
        serializer.save(reported_by=self.request.user, created_by=self.request.user)


# ---------------- 线索多次跟进记录 ----------------
class LeadFollowUpViewSet(viewsets.ModelViewSet):
    """线索跟进记录（第一次 / 二次 / 三次，支持多次添加）"""
    queryset = LeadFollowUp.objects.filter(is_deleted=False).select_related("lead_ext")
    serializer_class = LeadFollowUpSerializer
    ordering_fields = ["round_no", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("lead_ext"):
            qs = qs.filter(lead_ext_id=self.request.query_params["lead_ext"])
        return qs.order_by("round_no", "created_at")

    def perform_create(self, serializer):
        data = serializer.validated_data
        if data.get("deal_happened"):
            # 某次跟进成交：回写线索签单金额（取最新一次），并标记原线索已成交
            ext = data.get("lead_ext")
            if ext:
                ext.deal_amount = data.get("deal_amount") or ext.deal_amount
                ext.save(update_fields=["deal_amount"])
                if ext.lead and ext.lead.status != "DEAL":
                    ext.lead.status = "DEAL"
                    ext.lead.dealt_at = timezone.now()
                    ext.lead.save(update_fields=["status", "dealt_at"])
        serializer.save(created_by=self.request.user)


# ---------------- 外勤精细化进度节点 ----------------
class FieldTaskNodeViewSet(viewsets.ModelViewSet):
    """外勤任务进度节点（资料确认/办理执照/刻章/银行开户/税务登记）

    权限：外勤人员 / 外勤主管 / 管理层可上报与更新节点进度（颜色标记 + 完成日期）。
    """
    queryset = FieldTaskNode.objects.filter(is_deleted=False).select_related("task")
    serializer_class = FieldTaskNodeSerializer
    permission_classes = [IsFieldOrAdmin]
    ordering_fields = ["order", "id"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("task"):
            qs = qs.filter(task_id=self.request.query_params["task"])
        return qs.order_by("order", "id")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# ---------------- 增值业务部 ----------------
class ValueAddedProjectViewSet(viewsets.ModelViewSet):
    """增值业务部项目台账（独立数据台账 + 独立权限）"""
    queryset = ValueAddedProject.objects.filter(is_deleted=False)
    serializer_class = ValueAddedProjectSerializer
    search_fields = ["name", "customer_name", "project_type"]
    ordering_fields = ["created_at", "amount"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = scope_projects(qs, self.request.user)
        if self.request.query_params.get("status"):
            qs = qs.filter(status=self.request.query_params["status"])
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        data = serializer.validated_data
        if data.get("owner") is None:
            serializer.save(owner=self.request.user, created_by=self.request.user)
        else:
            serializer.save(created_by=self.request.user)

    # ---------- 增值业务合同上传（续费 / 上门拜访场景）----------
    @action(detail=True, methods=["post"])
    def upload_contract(self, request, pk=None):
        """本地上传 PDF 电子合同 / 合同扫描件（预留后期对接第三方电子签章跳转）"""
        proj = self.get_object()
        if not (can_view_all(request.user) or proj.owner_id == request.user.id):
            return Response({"detail": "无权操作该项目"}, status=status.HTTP_403_FORBIDDEN)
        f = request.FILES.get("contract")
        if not f:
            return Response({"detail": "未收到文件"}, status=status.HTTP_400_BAD_REQUEST)
        proj.contract_attachment.save(f.name, f, save=True)
        return Response({"detail": "已上传", "url": proj.contract_attachment.url})


# ---------------- 投放消耗 ----------------
class AdSpendRecordViewSet(viewsets.ModelViewSet):
    """投放消耗记录（按平台/账号/日期，用于投产比统计）"""
    queryset = AdSpendRecord.objects.filter(is_deleted=False)
    serializer_class = AdSpendRecordSerializer
    ordering_fields = ["stat_date", "cost"]

    def get_queryset(self):
        qs = super().get_queryset()
        if not can_view_all(self.request.user):
            qs = qs.filter(owner=self.request.user)
        p = self.request.query_params
        if p.get("channel"):
            qs = qs.filter(channel_id=p["channel"])
        if p.get("start") and p.get("end"):
            qs = qs.filter(stat_date__range=[p["start"], p["end"]])
        return qs.order_by("-stat_date")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user, created_by=self.request.user)


# ---------------- 成交师 × 平台 专项分配 ----------------
class CloserChannelViewSet(viewsets.ModelViewSet):
    """成交师平台专项分配（按平台派单的绑定关系，仅管理员维护）"""
    queryset = CloserChannel.objects.filter(is_deleted=False).select_related("user", "channel")
    serializer_class = CloserChannelSerializer
    permission_classes = [IsGrowthAdmin]
    ordering_fields = ["priority", "id"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("channel"):
            qs = qs.filter(channel_id=self.request.query_params["channel"])
        if self.request.query_params.get("user"):
            qs = qs.filter(user_id=self.request.query_params["user"])
        return qs.order_by("-priority", "id")

    @action(detail=False, methods=["get"])
    def matrix(self, request):
        """分配矩阵：每个平台由哪些成交师负责"""
        from collections import defaultdict
        data = defaultdict(list)
        for b in self.get_queryset():
            data[str(b.channel_id)].append({
                "binding_id": b.id,
                "user": b.user_id,
                "user_name": getattr(b.user, "display_name", None) or b.user.username,
                "priority": b.priority,
                "is_active": b.is_active,
            })
        return Response(dict(data))


# ---------------- 角色管理 ----------------
class GrowthRoleViewSet(viewsets.ModelViewSet):
    """增长中心角色分配（成交师 / 外勤 / 增值业务 / 运营）"""
    queryset = GrowthRole.objects.filter(is_deleted=False)
    serializer_class = GrowthRoleSerializer
    permission_classes = [IsGrowthAdmin]

    def get_queryset(self):
        return super().get_queryset().select_related("user").order_by("id")

    @action(detail=False, methods=["get"],
            permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """当前登录人的增长中心角色（任何登录用户可看自己的）"""
        r = getattr(request.user, "growth_role", None)
        if not r:
            return Response({"has_role": False, "can_view_all": can_view_all(request.user)})
        return Response({
            "has_role": True,
            "role": r.role,
            "role_label": r.get_role_display(),
            "dept_key": r.dept_key,
            "can_view_all": can_view_all(request.user),
        })
