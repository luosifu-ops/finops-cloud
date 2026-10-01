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
