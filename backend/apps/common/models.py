"""通用基类模型"""
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField("已删除", default=False)
    deleted_at = models.DateTimeField("删除时间", null=True, blank=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])


class BaseModel(TimeStampedModel, SoftDeleteModel):
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="%(app_label)s_%(class)s_created", verbose_name="创建人",
    )

    # 自动编号配置：子类声明 {"字段名": "前缀"}，保存时若字段为空则自动生成
    AUTO_NO_FIELDS = {}

    def save(self, *args, **kwargs):
        for field, prefix in self.AUTO_NO_FIELDS.items():
            from apps.common.auto_no import ensure_no
            ensure_no(self, field, prefix)
        super().save(*args, **kwargs)

    class Meta:
        abstract = True


class OperationLog(TimeStampedModel):
    """全站操作日志（2026-10-29 Boss 全局规则6）：谁在什么时间对什么对象做了什么"""
    ACTIONS = [
        ("CREATE", "新增"), ("UPDATE", "修改"), ("DELETE", "删除"), ("BULK_DELETE", "批量删除"),
        ("IMPORT", "导入"), ("EXPORT", "导出"), ("APPROVE", "审批通过"), ("REJECT", "审批驳回"),
        ("ASSIGN", "分配"), ("RETURN", "退回"), ("LOGIN", "登录"), ("OTHER", "其他"),
    ]
    user = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
                             related_name="op_logs", verbose_name="操作人")
    user_name = models.CharField("操作人姓名", max_length=50, blank=True, default="")
    action = models.CharField("动作", max_length=20, choices=ACTIONS, default="OTHER")
    module = models.CharField("功能模块", max_length=50, blank=True, default="")
    object_type = models.CharField("对象类型", max_length=60, blank=True, default="")
    object_id = models.CharField("对象ID", max_length=50, blank=True, default="")
    object_repr = models.CharField("对象摘要", max_length=200, blank=True, default="")
    detail = models.TextField("变更明细", blank=True, default="")
    ip = models.GenericIPAddressField("IP", null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "操作日志"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.user_name} {self.get_action_display()} {self.object_repr}"


class SystemConfig(TimeStampedModel):
    """系统键值配置（第三方API密钥等，可视化维护，避免改代码/改环境变量）"""
    key = models.CharField("配置键", max_length=100, unique=True)
    value = models.TextField("配置值", blank=True, default="")
    remark = models.CharField("说明", max_length=200, blank=True, default="")
    updated_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="sys_configs_updated", verbose_name="最后修改人")

    class Meta:
        ordering = ["key"]
        verbose_name = "系统配置"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.key

    @classmethod
    def get(cls, key, default=""):
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set(cls, key, value, remark="", user=None):
        obj, _ = cls.objects.update_or_create(key=key, defaults={"value": value, "remark": remark, "updated_by": user})
        return obj


class InboxMessage(TimeStampedModel):
    """站内消息（审批结果通知等，2026-10-29 Boss 全局规则5）"""
    recipient = models.ForeignKey("accounts.User", on_delete=models.CASCADE,
                                  related_name="inbox_messages", verbose_name="接收人")
    title = models.CharField("标题", max_length=200)
    body = models.TextField("内容", blank=True, default="")
    category = models.CharField("类型", max_length=30, blank=True, default="APPROVAL")
    link = models.CharField("跳转路径", max_length=200, blank=True, default="")
    is_read = models.BooleanField("已读", default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "站内消息"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title
