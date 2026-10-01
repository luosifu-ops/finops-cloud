"""独立招商板块（对外展示合作政策、招商资料、合作咨询提交）"""
from django.db import models
from apps.common.models import BaseModel


class InvestPolicy(BaseModel):
    """合作政策（对外展示）"""
    title = models.CharField("政策标题", max_length=200)
    content = models.TextField("政策正文")
    sort_order = models.IntegerField("排序", default=0)
    is_published = models.BooleanField("已发布", default=True)

    class Meta:
        verbose_name = "合作政策"
        verbose_name_plural = verbose_name
        ordering = ["sort_order", "-created_at"]

    def __str__(self):
        return self.title


class InvestMaterial(BaseModel):
    """招商资料"""
    CATEGORY = [
        ("MANUAL", "合作手册"),
        ("MODEL", "收益模型"),
        ("CASE", "成功案例"),
        ("BRAND", "品牌素材"),
    ]
    title = models.CharField("资料标题", max_length=200)
    category = models.CharField("分类", max_length=20, choices=CATEGORY, default="MANUAL")
    summary = models.CharField("摘要", max_length=300, blank=True)
    file_url = models.CharField("资料链接", max_length=300, blank=True, help_text="外链/下载地址")
    cover = models.CharField("封面图URL", max_length=300, blank=True)
    sort_order = models.IntegerField("排序", default=0)

    class Meta:
        verbose_name = "招商资料"
        verbose_name_plural = verbose_name
        ordering = ["category", "sort_order", "-created_at"]

    def __str__(self):
        return self.title


class InvestInquiry(BaseModel):
    """合作咨询提交"""
    STATUS = [
        ("NEW", "待跟进"),
        ("CONTACTED", "已联系"),
        ("DONE", "已成交/结束"),
    ]
    name = models.CharField("姓名", max_length=50)
    phone = models.CharField("联系电话", max_length=20)
    company = models.CharField("公司名称", max_length=200, blank=True)
    city = models.CharField("城市", max_length=100, blank=True)
    message = models.TextField("咨询留言", blank=True)
    status = models.CharField("状态", max_length=20, choices=STATUS, default="NEW")

    class Meta:
        verbose_name = "合作咨询"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name}-{self.phone}"
