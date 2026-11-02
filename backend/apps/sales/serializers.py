"""电销部：序列化器"""
from rest_framework import serializers
from .models import (
    Lead, Customer, Contract, CallRecord, FollowUp, SalesTarget, CommissionRule, SalaryRecord,
    Streamer, CustomerTag,
)


class LeadSerializer(serializers.ModelSerializer):
    """销售线索"""
    owner_name = serializers.CharField(source="owner.display_name", read_only=True)
    assigned_by_name = serializers.SerializerMethodField()
    source_name = serializers.CharField(source="get_source_display", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)
    level_name = serializers.CharField(source="get_level_display", read_only=True)

    class Meta:
        model = Lead
        fields = [
            "id", "lead_no", "name", "phone", "wechat", "company", "source", "source_name",
            "source_detail", "intention", "level", "level_name",
            "status", "status_name", "owner", "owner_name", "assigned_by", "assigned_by_name",
            "ops_record",
            "remark", "lost_reason", "assigned_at", "dealt_at",
            "created_at", "updated_at",
        ]
        read_only_fields = ["assigned_at", "dealt_at", "created_at", "updated_at"]

    def get_assigned_by_name(self, obj):
        return obj.assigned_by.display_name or obj.assigned_by.username if obj.assigned_by else None


class CustomerSerializer(serializers.ModelSerializer):
    """客户档案（2026-10-29 增加标签体系：tags 写入标签 id 列表，tags_info 读出名称+配色）"""
    owner_name = serializers.CharField(source="owner.display_name", read_only=True)
    accountant_name = serializers.CharField(source="accountant.display_name", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)
    customer_type_name = serializers.CharField(source="get_customer_type_display", read_only=True)
    tags_info = serializers.SerializerMethodField()
    tags = serializers.PrimaryKeyRelatedField(
        many=True, queryset=CustomerTag.objects.filter(is_deleted=False), required=False)

    def get_tags_info(self, obj):
        return [{"id": t.id, "name": t.name, "color": t.color} for t in obj.tags.all()]

    class Meta:
        model = Customer
        fields = [
            "id", "name", "short_name", "customer_type", "customer_type_name",
            "contact", "phone", "wechat", "credit_code", "industry", "region",
            "address", "source", "owner", "owner_name", "accountant", "accountant_name",
            "level", "status", "status_name", "signed_at", "expire_at", "remark",
            "tags", "tags_info", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class ContractSerializer(serializers.ModelSerializer):
    """合同订单"""
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    lead_name = serializers.CharField(source="lead.name", read_only=True)
    sales_name = serializers.CharField(source="sales.display_name", read_only=True)
    biz_type_name = serializers.CharField(source="get_biz_type_display", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)
    pay_type_name = serializers.CharField(source="get_pay_type_display", read_only=True)
    receivable = serializers.ReadOnlyField()
    # 合同扫描件下载地址：固定返回站内相对路径（如 /media/contract/xx.pdf）
    # 不用 DRF 默认的绝对 URL —— 网关回源域名与对外域名不一致，绝对 URL 会指向内网打不开
    attachment_url = serializers.SerializerMethodField()
    # 客户付款截图地址（增量功能）
    payment_screenshot_url = serializers.SerializerMethodField()
    # 派单人姓名（主管可编辑权限：显示指派给签单销售的人）
    assigned_by_name = serializers.SerializerMethodField()

    def get_attachment_url(self, obj):
        try:
            return obj.attachment.url if obj.attachment else ""
        except ValueError:
            return ""

    def get_payment_screenshot_url(self, obj):
        try:
            return obj.payment_screenshot.url if obj.payment_screenshot else ""
        except ValueError:
            return ""

    def get_assigned_by_name(self, obj):
        return obj.assigned_by.display_name or obj.assigned_by.username if obj.assigned_by else None

    class Meta:
        model = Contract
        fields = [
            "id", "contract_no", "customer", "customer_name", "lead", "lead_name",
            "biz_type", "biz_type_name", "title", "amount", "received", "receivable",
            "pay_type", "pay_type_name", "service_period", "sales", "sales_name",
            "assigned_by", "assigned_by_name",
            "status", "status_name", "signed_date", "start_date", "end_date",
            "attachment", "attachment_url",
            "payment_screenshot", "payment_screenshot_url",
            "remark", "created_at", "updated_at",
        ]
        read_only_fields = ["received", "receivable", "created_at", "updated_at",
                            "attachment", "attachment_url",
                            "payment_screenshot", "payment_screenshot_url"]


class CallRecordSerializer(serializers.ModelSerializer):
    """通话记录"""
    user_name = serializers.CharField(source="user.display_name", read_only=True)
    lead_name = serializers.CharField(source="lead.name", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    result_name = serializers.CharField(source="get_result_display", read_only=True)

    class Meta:
        model = CallRecord
        fields = [
            "id", "user", "user_name", "lead", "lead_name", "customer", "customer_name",
            "phone", "duration", "result", "result_name", "has_wechat", "summary", "created_at",
        ]
        read_only_fields = ["created_at"]
        extra_kwargs = {"user": {"required": False}}


class FollowUpSerializer(serializers.ModelSerializer):
    """跟进记录"""
    lead_name = serializers.CharField(source="lead.name", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    user_name = serializers.CharField(source="user.display_name", read_only=True)
    way_name = serializers.CharField(source="get_way_display", read_only=True)

    class Meta:
        model = FollowUp
        fields = [
            "id", "lead", "lead_name", "customer", "customer_name",
            "user", "user_name", "way", "way_name", "content",
            "next_at", "next_action", "created_at", "updated_at",
        ]
        # user 由 perform_create 按当前登录人自动写入，避免创建时必填报错（同时修复既有跟进页）
        read_only_fields = ["created_at", "updated_at", "user"]


class SalesTargetSerializer(serializers.ModelSerializer):
    """业绩目标"""
    department_name = serializers.CharField(source="department.name", read_only=True)
    team_name = serializers.CharField(source="team.name", read_only=True)
    user_name = serializers.CharField(source="user.display_name", read_only=True)
    scope_name = serializers.CharField(source="get_scope_display", read_only=True)

    class Meta:
        model = SalesTarget
        fields = [
            "id", "month", "scope", "scope_name", "department", "department_name",
            "team", "team_name", "user", "user_name",
            "amount_target", "order_target", "call_target",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class CommissionRuleSerializer(serializers.ModelSerializer):
    """提成规则"""
    department_name = serializers.CharField(source="department.name", read_only=True)
    rule_type_name = serializers.CharField(source="get_rule_type_display", read_only=True)

    class Meta:
        model = CommissionRule
        fields = [
            "id", "name", "rule_type", "rule_type_name", "department", "department_name",
            "rate", "fixed_amount", "ladder", "effective_month", "remark",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class SalaryRecordSerializer(serializers.ModelSerializer):
    """工资核算记录"""
    user_name = serializers.CharField(source="user.display_name", read_only=True)

    class Meta:
        model = SalaryRecord
        fields = [
            "id", "user", "user_name", "month", "base_salary", "performance",
            "commission", "commission_rule", "bonus", "deduction", "total",
            "settled", "remark", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "total"]

    def validate(self, attrs):
        # 自动计算实发工资
        base = attrs.get("base_salary") or 0
        comm = attrs.get("commission") or 0
        bonus = attrs.get("bonus") or 0
        deduct = attrs.get("deduction") or 0
        attrs["total"] = round(base + comm + bonus - deduct, 2)
        return attrs


class StreamerSerializer(serializers.ModelSerializer):
    """主播"""
    department_name = serializers.CharField(source="department.name", read_only=True)
    manager_name = serializers.CharField(source="manager.display_name", read_only=True)
    platform_name = serializers.CharField(source="get_platform_display", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Streamer
        fields = [
            "id", "name", "real_name", "platform", "platform_name", "account", "phone",
            "department", "department_name", "manager", "manager_name",
            "status", "status_name", "entry_date", "fans_count", "live_count",
            "gmv", "commission_rate", "remark", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class CustomerTagSerializer(serializers.ModelSerializer):
    """客户标签（2026-10-29 客户档案标签体系）"""
    customer_count = serializers.SerializerMethodField()

    def get_customer_count(self, obj):
        return obj.customers.filter(is_deleted=False).count()

    class Meta:
        model = CustomerTag
        fields = ["id", "name", "color", "sort", "is_active", "remark", "customer_count",
                  "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]
