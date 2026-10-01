"""合同订单名录：序列化器"""
from rest_framework import serializers
from .models import ContractRecord, ContractFile


class ContractFileSerializer(serializers.ModelSerializer):
    file_type_label = serializers.CharField(source="get_file_type_display", read_only=True)
    url = serializers.SerializerMethodField()

    class Meta:
        model = ContractFile
        fields = ["id", "record", "file_type", "file_type_label", "file", "url", "created_at"]
        read_only_fields = ["id", "created_at", "url"]

    def get_url(self, obj):
        return obj.file.url if obj.file else ""


class ContractRecordSerializer(serializers.ModelSerializer):
    dept_label = serializers.CharField(source="get_dept_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    signer_name = serializers.SerializerMethodField()
    files = ContractFileSerializer(many=True, read_only=True)

    class Meta:
        model = ContractRecord
        fields = [
            "id", "dept", "dept_label", "company_name", "credit_code",
            "service_content", "service_period", "amount", "signed_date",
            "recv_account", "customer_phone", "signer", "signer_name",
            "status", "status_label", "remark", "files", "created_at",
        ]
        read_only_fields = ["id", "created_at", "signer_name", "files"]

    def get_signer_name(self, obj):
        if not obj.signer:
            return ""
        return (getattr(obj.signer, "display_name", None)
                or obj.signer.get_full_name() or obj.signer.username)


class ContractRecordCreateSerializer(serializers.ModelSerializer):
    """录入合同（签单人默认当前登录人）"""
    class Meta:
        model = ContractRecord
        fields = [
            "dept", "company_name", "credit_code", "service_content",
            "service_period", "amount", "signed_date", "recv_account",
            "customer_phone", "status", "remark",
        ]

    def validate_company_name(self, v):
        if not v or not v.strip():
            raise serializers.ValidationError("企业名称必填")
        return v

    def validate_amount(self, v):
        if v is None or v < 0:
            raise serializers.ValidationError("签单金额须 ≥ 0")
        return v
