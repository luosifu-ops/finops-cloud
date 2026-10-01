"""系统资源对接配置 — 序列化器（纯新增）"""
from rest_framework import serializers

from .models import CloudResourceConfig


class CloudResourceConfigSerializer(serializers.ModelSerializer):
    provider_label = serializers.CharField(source="get_provider_display", read_only=True)
    resource_type_label = serializers.CharField(source="get_resource_type_display", read_only=True)
    # 密钥脱敏（列表/详情都返回空字符串占位）
    access_key_secret_masked = serializers.SerializerMethodField()

    class Meta:
        model = CloudResourceConfig
        fields = [
            "id", "provider", "provider_label",
            "resource_type", "resource_type_label",
            "name", "endpoint", "region",
            "access_key_id", "access_key_secret_enc", "access_key_secret_masked",
            "bucket_or_instance",
            "capacity_gb", "capacity_max_gb",
            "last_check_at", "last_check_ok", "last_check_msg",
            "notes", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "last_check_at",
                            "last_check_ok", "last_check_msg", "access_key_secret_masked"]
        extra_kwargs = {
            "access_key_secret_enc": {"write_only": True},
        }

    def get_access_key_secret_masked(self, obj):
        if obj.access_key_secret_enc:
            return "******" + (obj.access_key_secret_enc[-4:] if len(obj.access_key_secret_enc) > 4 else "")
        return ""

    def validate_endpoint(self, v):
        """禁止第三方中间商域名：仅允许腾讯云/阿里云官方 endpoint"""
        v = (v or "").strip().lower()
        if not v:
            raise serializers.ValidationError("endpoint 不能为空")
        if not (v.startswith("http://") or v.startswith("https://")):
            raise serializers.ValidationError("endpoint 必须以 http:// 或 https:// 开头")
        # 官方 endpoint 校验（部分示例，扩展白名单需更新此处）
        official_keywords = (
            # 腾讯云
            "tencentcloud", "tencent.com.cn", "dnspod.cn", "qcloud.com",
            # 阿里云
            "aliyuncs.com", "aliyun.com", "dns.alidns.com",
        )
        if not any(k in v for k in official_keywords):
            raise serializers.ValidationError(
                "endpoint 非官方域名，仅允许腾讯云/阿里云官方接入点（禁止第三方中间商）"
            )
        return v
