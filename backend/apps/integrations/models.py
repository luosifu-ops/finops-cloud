"""系统资源对接配置（纯新增）

【Boss 2026-09-07 指示】
- 域名 / 存储 / 服务器资源 直连 腾讯、阿里 官方渠道，禁用第三方中间商
- 支持按需扩容（容量可调）
- 仅管理员/管理层可配置（permission IsResourceAdmin）

实现要点
- CloudResourceConfig 存对接配置（endpoint / access_key 等敏感字段只存密文）
- 不引入第三方 SDK（避免中间商依赖），仅校验 endpoint 在官方域名白名单内
- /check/ 健康检测：纯原生 TCP/HTTP 探活，未来可平滑替换为官方 SDK
"""
from django.db import models

from apps.common.models import BaseModel


class CloudResourceConfig(BaseModel):
    """云资源对接配置（域名 / 存储 / 服务器 直连官方）"""

    class PROVIDER(models.TextChoices):
        TENCENT = "TENCENT", "腾讯云"
        ALI = "ALI", "阿里云"

    class RESOURCE_TYPE(models.TextChoices):
        DOMAIN = "DOMAIN", "域名 DNS"
        STORAGE = "STORAGE", "对象存储"
        SERVER = "SERVER", "云服务器"
        DATABASE = "DATABASE", "云数据库"

    provider = models.CharField("云厂商", max_length=16, choices=PROVIDER.choices)
    resource_type = models.CharField("资源类型", max_length=16, choices=RESOURCE_TYPE.choices)
    name = models.CharField("资源名", max_length=80)
    endpoint = models.CharField("官方接入点(Endpoint URL)", max_length=200,
                                help_text="仅允许腾讯云或阿里云官方 endpoint，禁止第三方域名")
    region = models.CharField("地域", max_length=40, blank=True, default="",
                              help_text="如 ap-guangzhou / cn-hangzhou 等官方地域 ID")

    # 凭据（默认加密存，未来可改为 KMS）
    access_key_id = models.CharField("AccessKeyId", max_length=64, blank=True, default="")
    access_key_secret_enc = models.TextField("AccessKeySecret(密文)", blank=True, default="")

    # 资源标识
    bucket_or_instance = models.CharField("桶名/实例ID", max_length=200, blank=True, default="")

    # 容量（按需扩容）
    capacity_gb = models.PositiveIntegerField("当前容量(GB)", default=0, help_text="0 表示不适用（域名/服务器）")
    capacity_max_gb = models.PositiveIntegerField("最大可扩容(GB)", default=0, help_text="0 表示不限")

    # 健康检测
    last_check_at = models.DateTimeField("最近检测时间", null=True, blank=True)
    last_check_ok = models.BooleanField("最近检测结果", default=False)
    last_check_msg = models.CharField("最近检测信息", max_length=200, blank=True, default="")

    notes = models.CharField("备注", max_length=300, blank=True, default="")

    class Meta:
        db_table = "sys_cloud_resource_config"
        verbose_name = "云资源对接"
        verbose_name_plural = "云资源对接"
        ordering = ["provider", "resource_type", "-created_at"]

    def provider_label(self):
        return self.get_provider_display()

    def resource_type_label(self):
        return self.get_resource_type_display()

    def __str__(self):
        return f"{self.get_provider_display()}-{self.get_resource_type_display()}-{self.name}"
