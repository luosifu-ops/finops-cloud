"""增长中心：序列化器（纯新增，不改动任何既有 serializer）"""
from rest_framework import serializers
from django.utils import timezone

from apps.sales.models import Lead
from .models import (
    LeadChannel, LeadExt, LeadFlow, LeadPool, LeadStageLog,
    FieldTask, FieldProgress, ValueAddedProject, AdSpendRecord, GrowthRole,
    CloserChannel, LeadFollowUp, FieldTaskNode,
)


def _user_name(u):
    """用户显示名（容错：优先 display_name，其次姓名/用户名）"""
    if not u:
        return ""
    return (getattr(u, "display_name", None)
            or u.get_full_name()
            or u.username
            or "")


# ---------------- 渠道 ----------------
class LeadChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadChannel
        fields = ["id", "code", "name", "is_enabled", "is_reserved", "sort", "created_at"]
        read_only_fields = ["created_at"]


# ---------------- 角色 ----------------
class GrowthRoleSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    role_label = serializers.CharField(source="get_role_display", read_only=True)
    dept_label = serializers.CharField(source="get_dept_key_display", read_only=True)

    class Meta:
        model = GrowthRole
        fields = ["id", "user", "user_name", "role", "role_label",
                  "dept_key", "dept_label", "can_view_all"]
        read_only_fields = ["id"]

    def get_user_name(self, obj):
        return _user_name(obj.user)


# ---------------- 线索扩展 ----------------
class LeadFlowSerializer(serializers.ModelSerializer):
    action_label = serializers.CharField(source="get_action_display", read_only=True)
    from_user_name = serializers.SerializerMethodField()
    to_user_name = serializers.SerializerMethodField()

    class Meta:
        model = LeadFlow
        fields = ["id", "lead_ext", "action", "action_label",
                  "from_user", "from_user_name", "to_user", "to_user_name",
                  "remark", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_from_user_name(self, obj):
        return _user_name(obj.from_user)

    def get_to_user_name(self, obj):
        return _user_name(obj.to_user)


class LeadStageLogSerializer(serializers.ModelSerializer):
    new_stage_label = serializers.CharField(source="get_new_stage_display", read_only=True)

    class Meta:
        model = LeadStageLog
        fields = ["id", "lead_ext", "old_stage", "new_stage", "new_stage_label", "remark", "created_at"]
        read_only_fields = ["id", "created_at"]


class LeadExtSerializer(serializers.ModelSerializer):
    """线索扩展信息（读）"""
    channel_name = serializers.CharField(source="channel.name", read_only=True)
    channel_code = serializers.CharField(source="channel.code", read_only=True)
    # 2026-11-03 Boss 指示：线索池展示「录入人」（优先扩展记录创建人，回落到原线索创建人）
    creator_name = serializers.SerializerMethodField()
    ops_owner_name = serializers.SerializerMethodField()
    closer_name = serializers.SerializerMethodField()
    stage_label = serializers.CharField(source="get_stage_3570_display", read_only=True)
    contact_type_label = serializers.CharField(source="get_contact_type_display", read_only=True)
    # 关联原线索的关键信息（只读展示，不改动 Lead）
    lead_name = serializers.CharField(source="lead.name", read_only=True)
    lead_phone = serializers.CharField(source="lead.phone", read_only=True)
    lead_status = serializers.CharField(source="lead.status", read_only=True)
    lead_intention = serializers.CharField(source="lead.intention", read_only=True)
    # 2026-09-12 增量：成交与转化率（只读派生）
    is_deal = serializers.BooleanField(read_only=True)
    conversion_rate = serializers.IntegerField(read_only=True)

    class Meta:
        model = LeadExt
        fields = [
            "id", "lead", "lead_name", "lead_phone", "lead_status", "lead_intention",
            "channel", "channel_name", "channel_code",
            "source_account_no", "contact_type", "contact_type_label", "contact_value",
            "creator_name",
            "ops_owner", "ops_owner_name", "closer", "closer_name",
            "stage_3570", "stage_label", "in_pool",
            "customer_need", "contact_person", "acquisition_cost", "deal_amount",
            "is_deal", "conversion_rate", "extra", "created_at",
        ]
        read_only_fields = ["id", "created_at", "is_deal", "conversion_rate"]

    def get_ops_owner_name(self, obj):
        return _user_name(obj.ops_owner)

    def get_creator_name(self, obj):
        u = obj.created_by or getattr(getattr(obj, "lead", None), "created_by", None)
        return _user_name(u)

    def get_closer_name(self, obj):
        return _user_name(obj.closer)


class LeadExtCreateSerializer(serializers.Serializer):
    """运营录入线索（一次提交 = 原线索 Lead + 扩展信息 LeadExt）

    必填：来源平台、来源账号编号、客户联系方式、归属运营人（自动取当前登录人）
    """
    # --- 原 Lead 需要的字段（新增记录，不改动 Lead 模型） ---
    name = serializers.CharField(label="客户姓名", max_length=50)
    phone = serializers.CharField(label="联系电话", max_length=30, required=False, allow_blank=True)
    wechat = serializers.CharField(label="微信", max_length=60, required=False, allow_blank=True)
    company = serializers.CharField(label="公司名称", max_length=200, required=False, allow_blank=True)
    intention = serializers.CharField(label="意向业务", max_length=100, required=False, allow_blank=True)

    # --- 扩展必填字段 ---
    channel = serializers.PrimaryKeyRelatedField(queryset=LeadChannel.objects.filter(is_deleted=False),
                                                 label="线索来源平台")
    source_account_no = serializers.CharField(label="来源账号编号", max_length=100)
    contact_type = serializers.ChoiceField(label="客户联系方式", choices=LeadExt.CONTACT_TYPE)
    contact_value = serializers.CharField(label="联系方式内容", max_length=100, required=False, allow_blank=True)
    remark = serializers.CharField(label="备注", required=False, allow_blank=True)
    # 2026-09-12 增量：录入中心字段
    customer_need = serializers.CharField(label="客户需求", required=False, allow_blank=True)
    contact_person = serializers.CharField(label="对接人", required=False, allow_blank=True)
    acquisition_cost = serializers.DecimalField(label="获客成本(元)", max_digits=12, decimal_places=2,
                                                required=False, default=0)
    deal_amount = serializers.DecimalField(label="签单金额(元)", max_digits=14, decimal_places=2,
                                           required=False, default=0)
    # 指定成交师（不传则系统按负载自动流转）
    closer = serializers.IntegerField(label="指定成交师", required=False, allow_null=True)

    def validate(self, attrs):
        if attrs.get("contact_type") == "PHONE" and not attrs.get("phone"):
            raise serializers.ValidationError("联系方式为电话时，联系电话必填")
        if attrs.get("contact_type") == "WECHAT" and not (attrs.get("wechat") or attrs.get("phone")):
            raise serializers.ValidationError("联系方式为微信时，微信或电话至少填一项")
        if not attrs.get("phone") and not attrs.get("wechat"):
            raise serializers.ValidationError("电话与微信至少填一项")
        return attrs


# ---------------- 公海 ----------------
class LeadPoolSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    returned_by_name = serializers.SerializerMethodField()
    claimed_by_name = serializers.SerializerMethodField()
    # 2026-11-03 Boss 指示：线索池展示「录入人姓名」（取线索的 created_by）
    creator_name = serializers.SerializerMethodField()
    lead_name = serializers.CharField(source="lead_ext.lead.name", read_only=True)
    lead_phone = serializers.CharField(source="lead_ext.lead.phone", read_only=True)
    channel_name = serializers.CharField(source="lead_ext.channel.name", read_only=True)

    class Meta:
        model = LeadPool
        fields = ["id", "lead_ext", "lead_name", "lead_phone", "channel_name",
                  "creator_name",
                  "status", "status_label", "returned_by", "returned_by_name",
                  "returned_reason", "returned_at", "claimed_by", "claimed_by_name",
                  "claimed_at", "claim_count", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_creator_name(self, obj):
        lead = getattr(obj.lead_ext, "lead", None)
        u = getattr(lead, "created_by", None)
        if u and getattr(u, "id", None):
            return getattr(u, "display_name", None) or u.username
        return ""

    def get_returned_by_name(self, obj):
        return _user_name(obj.returned_by)

    def get_claimed_by_name(self, obj):
        return _user_name(obj.claimed_by)


# ---------------- 外勤 ----------------
class FieldProgressSerializer(serializers.ModelSerializer):
    reported_by_name = serializers.SerializerMethodField()

    class Meta:
        model = FieldProgress
        fields = ["id", "task", "node", "content", "reported_by", "reported_by_name", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_reported_by_name(self, obj):
        return _user_name(obj.reported_by)


class FieldTaskNodeSerializer(serializers.ModelSerializer):
    """外勤精细化进度节点"""
    node_label = serializers.CharField(source="get_node_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = FieldTaskNode
        fields = ["id", "task", "node", "node_label", "status", "status_label",
                  "done_at", "remark", "order", "created_at"]
        read_only_fields = ["id", "created_at"]


class LeadFollowUpSerializer(serializers.ModelSerializer):
    """线索多次跟进记录（第一次 / 二次 / 三次）"""
    round_label = serializers.CharField(source="get_round_no_display", read_only=True)
    way_label = serializers.CharField(source="get_way_display", read_only=True)

    class Meta:
        model = LeadFollowUp
        fields = ["id", "lead_ext", "round_no", "round_label", "way", "way_label",
                  "content", "follow_at", "deal_happened", "deal_amount", "created_at"]
        read_only_fields = ["id", "created_at"]


class FieldTaskSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    customer_type_label = serializers.CharField(source="get_customer_type_display", read_only=True)
    business_type_label = serializers.CharField(source="get_business_type_display", read_only=True)
    assignee_name = serializers.SerializerMethodField()
    assigned_by_name = serializers.SerializerMethodField()
    creator_name = serializers.SerializerMethodField()
    progresses = FieldProgressSerializer(many=True, read_only=True)
    nodes = FieldTaskNodeSerializer(many=True, read_only=True)
    latest_node = serializers.SerializerMethodField()

    class Meta:
        model = FieldTask
        fields = ["id", "task_no", "title", "order_no", "customer_name", "customer_type", "customer_type_label",
                  "from_order_no", "from_deal_id", "business_type", "business_type_label",
                  "task_type", "address",
                  "assignee", "assignee_name", "assigned_by", "assigned_by_name",
                  "creator", "creator_name",
                  "status", "status_label", "due_at", "accepted_at", "finished_at",
                  "remark", "progresses", "nodes", "latest_node", "created_at"]
        read_only_fields = ["id", "created_at", "accepted_at", "finished_at"]

    def get_assignee_name(self, obj):
        # 优先返回主管手动录入的外勤人员姓名；无录入时回退到系统用户姓名
        if obj.assignee_name:
            return obj.assignee_name
        return _user_name(obj.assignee)

    def get_assigned_by_name(self, obj):
        return obj.assigned_by.display_name or obj.assigned_by.username if obj.assigned_by else None

    def get_creator_name(self, obj):
        return _user_name(obj.creator)

    def get_latest_node(self, obj):
        # 优先取结构化节点里最新的一条进行中/已完成的， sales 可实时看到外勤办到哪
        p = obj.nodes.filter(is_deleted=False).exclude(status="PENDING").order_by("-updated_at").first()
        if p:
            return f"{p.get_node_display()}（{p.get_status_display()}）"
        p = obj.nodes.filter(is_deleted=False).first()
        return f"{p.get_node_display()}（待处理）" if p else ""


# ---------------- 增值业务部 ----------------
class ValueAddedProjectSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    owner_name = serializers.SerializerMethodField()
    profit = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = ValueAddedProject
        fields = ["id", "name", "customer_name", "project_type", "owner", "owner_name",
                  "amount", "cost", "profit", "status", "status_label",
                  "started_at", "finished_at", "remark", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_owner_name(self, obj):
        return _user_name(obj.owner)


# ---------------- 成交师 × 平台 专项分配 ----------------
class CloserChannelSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    channel_name = serializers.CharField(source="channel.name", read_only=True)
    channel_code = serializers.CharField(source="channel.code", read_only=True)

    class Meta:
        model = CloserChannel
        fields = ["id", "user", "user_name", "channel", "channel_name",
                  "channel_code", "priority", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_user_name(self, obj):
        return _user_name(obj.user)


# ---------------- 投放消耗 ----------------
class AdSpendRecordSerializer(serializers.ModelSerializer):
    channel_name = serializers.CharField(source="channel.name", read_only=True)
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = AdSpendRecord
        fields = ["id", "channel", "channel_name", "account_no", "stat_date",
                  "cost", "impressions", "clicks", "owner", "owner_name", "remark", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_owner_name(self, obj):
        return _user_name(obj.owner)
