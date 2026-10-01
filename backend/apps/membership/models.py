"""付费订阅 - 会员体系（面向对外销售给财税同行企业）"""
from django.db import models
from apps.common.models import BaseModel


class MembershipPlan(BaseModel):
    """会员套餐：不同等级开放不同系统功能权限"""
    code = models.CharField("套餐编码", max_length=20, unique=True, db_index=True)
    name = models.CharField("套餐名称", max_length=50)
    price_monthly = models.DecimalField("月价(元)", max_digits=10, decimal_places=2, default=0)
    price_yearly = models.DecimalField("年价(元)", max_digits=10, decimal_places=2, default=0)
    level = models.IntegerField("等级", default=0, help_text="数值越大等级越高")
    features = models.JSONField("套餐卖点", default=list, blank=True)
    permissions = models.JSONField(
        "开放功能权限", default=list, blank=True,
        help_text="功能 key 列表，如 dashboard/sales/accounting/hr/ops/onboarding/performance/reports/ai/investment/membership",
    )
    is_active = models.BooleanField("启用", default=True)
    sort_order = models.IntegerField("排序", default=0)

    class Meta:
        verbose_name = "会员套餐"
        verbose_name_plural = verbose_name
        ordering = ["level", "sort_order"]

    def __str__(self):
        return f"{self.name}({self.code})"


class Subscription(BaseModel):
    """订阅记录：某外部企业/联系人购买了哪个套餐"""
    STATUS = [
        ("PENDING", "待开通"),
        ("ACTIVE", "已开通"),
        ("EXPIRED", "已过期"),
        ("CANCELLED", "已取消"),
    ]
    PAY_METHOD = [
        ("WECHAT", "微信支付"),
        ("ALIPAY", "支付宝支付"),
        ("BANK", "对公转账"),
        ("OTHER", "其他"),
    ]
    company_name = models.CharField("企业名称", max_length=200)
    contact_name = models.CharField("联系人", max_length=50)
    phone = models.CharField("联系电话", max_length=20)
    plan = models.ForeignKey(
        MembershipPlan, on_delete=models.PROTECT,
        related_name="subscriptions", verbose_name="套餐")
    status = models.CharField("状态", max_length=20, choices=STATUS, default="PENDING")
    pay_method = models.CharField("支付方式", max_length=20, choices=PAY_METHOD, blank=True, default="")
    amount = models.DecimalField("实付金额(元)", max_digits=12, decimal_places=2, default=0)
    start_date = models.DateField("生效日期", null=True, blank=True)
    end_date = models.DateField("到期日期", null=True, blank=True)
    remark = models.TextField("备注", blank=True)

    class Meta:
        verbose_name = "会员订阅"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.company_name}-{self.plan.name}"
