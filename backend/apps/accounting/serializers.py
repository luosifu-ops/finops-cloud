"""会计部：序列化器"""
from rest_framework import serializers
from .models import (
    TaxType, AccountingClient, MonthlyTask, TaskStep, Voucher, Invoice,
    BankStatement, TaxDeclaration, SocialInsurance, AnnualReport,
    BusinessItem, ClientDocument, HandoverRecord,
)


class TaxTypeSerializer(serializers.ModelSerializer):
    """税种"""
    cycle_name = serializers.CharField(source="get_cycle_display", read_only=True)

    class Meta:
        model = TaxType
        fields = ["id", "name", "cycle", "cycle_name", "deadline_rule", "is_active",
                  "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class AccountingClientSerializer(serializers.ModelSerializer):
    """代账客户"""
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    accountant_name = serializers.CharField(source="accountant.display_name", read_only=True)
    assistant_name = serializers.CharField(source="assistant.display_name", read_only=True)
    taxpayer_type_name = serializers.CharField(source="get_taxpayer_type_display", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = AccountingClient
        fields = [
            "id", "customer", "customer_name", "accountant", "accountant_name",
            "assistant", "assistant_name", "taxpayer_type", "taxpayer_type_name",
            "tax_no", "tax_bureau", "ele_tax_account", "ele_tax_password",
            "ukey_password", "bank_account", "bank_name", "social_no",
            "status", "status_name", "service_start", "service_end",
            "monthly_fee", "zero_declare", "remark", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class MonthlyTaskSerializer(serializers.ModelSerializer):
    """月度做账任务"""
    client_name = serializers.CharField(source="client.customer.name", read_only=True)
    accountant_name = serializers.CharField(source="accountant.display_name", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = MonthlyTask
        fields = [
            "id", "client", "client_name", "period", "accountant", "accountant_name",
            "status", "status_name", "doc_received_at", "voucher_done_at",
            "declared_at", "deadline", "is_overdue", "income", "cost", "profit",
            "vat_amount", "surtax_amount", "cit_amount", "iit_amount", "stamp_amount",
            "total_tax", "zero_declare", "remark", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class TaskStepSerializer(serializers.ModelSerializer):
    """做账节点"""
    step_name = serializers.CharField(source="get_step_display", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)
    operator_name = serializers.CharField(source="operator.display_name", read_only=True)
    task_period = serializers.CharField(source="task.period", read_only=True)

    class Meta:
        model = TaskStep
        fields = ["id", "task", "task_period", "step", "step_name", "status", "status_name",
                  "operator", "operator_name", "finished_at", "remark",
                  "created_at", "updated_at"]
        read_only_fields = ["task", "step", "created_at", "updated_at"]


class VoucherSerializer(serializers.ModelSerializer):
    """记账凭证"""
    made_by_name = serializers.CharField(source="made_by.display_name", read_only=True)
    reviewed_by_name = serializers.CharField(source="reviewed_by.display_name", read_only=True)

    class Meta:
        model = Voucher
        fields = ["id", "task", "voucher_no", "date", "summary", "subject",
                  "debit", "credit", "attachment_count", "made_by", "made_by_name",
                  "reviewed_by", "reviewed_by_name", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class InvoiceSerializer(serializers.ModelSerializer):
    """发票"""
    client_name = serializers.CharField(source="client.customer.name", read_only=True)
    direction_name = serializers.CharField(source="get_direction_display", read_only=True)
    kind_name = serializers.CharField(source="get_kind_display", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Invoice
        fields = ["id", "task", "client", "client_name", "direction", "direction_name",
                  "kind", "kind_name", "code", "number", "invoice_date", "seller", "buyer",
                  "amount_ex_tax", "tax", "total", "tax_rate", "status", "status_name",
                  "file", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class BankStatementSerializer(serializers.ModelSerializer):
    """银行流水"""
    client_name = serializers.CharField(source="client.customer.name", read_only=True)

    class Meta:
        model = BankStatement
        fields = ["id", "client", "client_name", "task", "trans_date", "summary",
                  "counterparty", "income", "expense", "balance", "file",
                  "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class TaxDeclarationSerializer(serializers.ModelSerializer):
    """纳税申报"""
    client_name = serializers.CharField(source="task.client.customer.name", read_only=True)
    tax_type_name = serializers.CharField(source="tax_type.name", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)
    operator_name = serializers.CharField(source="operator.display_name", read_only=True)

    class Meta:
        model = TaxDeclaration
        fields = ["id", "task", "client_name", "tax_type", "tax_type_name", "period",
                  "deadline", "declared_at", "amount", "paid_amount", "status",
                  "status_name", "operator", "operator_name", "screenshot", "remark",
                  "created_at", "updated_at"]
        read_only_fields = ["declared_at", "created_at", "updated_at"]


class SocialInsuranceSerializer(serializers.ModelSerializer):
    """社保公积金"""
    client_name = serializers.CharField(source="client.customer.name", read_only=True)

    class Meta:
        model = SocialInsurance
        fields = ["id", "client", "client_name", "month", "person_count", "base_total",
                  "company_amount", "personal_amount", "total", "declared",
                  "declared_at", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class AnnualReportSerializer(serializers.ModelSerializer):
    """工商年报"""
    client_name = serializers.CharField(source="client.customer.name", read_only=True)
    operator_name = serializers.CharField(source="operator.display_name", read_only=True)

    class Meta:
        model = AnnualReport
        fields = ["id", "client", "client_name", "year", "deadline", "submitted",
                  "submitted_at", "operator", "operator_name", "created_at", "updated_at"]
        read_only_fields = ["submitted", "submitted_at", "created_at", "updated_at"]


class BusinessItemSerializer(serializers.ModelSerializer):
    """工商事项"""
    client_name = serializers.CharField(source="client.customer.name", read_only=True)
    item_type_name = serializers.CharField(source="get_item_type_display", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)
    handler_name = serializers.CharField(source="handler.display_name", read_only=True)

    class Meta:
        model = BusinessItem
        fields = ["id", "client", "client_name", "title", "item_type", "item_type_name",
                  "status", "status_name", "handler", "handler_name", "start_at",
                  "due_at", "finished_at", "progress", "fee", "result", "remark",
                  "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class ClientDocumentSerializer(serializers.ModelSerializer):
    """客户资料"""
    client_name = serializers.CharField(source="client.customer.name", read_only=True)
    kind_name = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = ClientDocument
        fields = ["id", "client", "client_name", "name", "kind", "kind_name", "file",
                  "expire_at", "version", "remark", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class HandoverRecordSerializer(serializers.ModelSerializer):
    """交接记录"""
    client_name = serializers.CharField(source="client.customer.name", read_only=True)
    from_user_name = serializers.CharField(source="from_user.display_name", read_only=True)
    to_user_name = serializers.CharField(source="to_user.display_name", read_only=True)

    class Meta:
        model = HandoverRecord
        fields = ["id", "client", "client_name", "from_user", "from_user_name",
                  "to_user", "to_user_name", "reason", "checklist", "confirmed",
                  "confirmed_at", "created_at", "updated_at"]
        read_only_fields = ["confirmed", "confirmed_at", "created_at", "updated_at"]
