"""合同订单名录（电销部 / 运营部 独立核算）

增量新模块，不改动既有 sales.Contract。
- ContractRecord：电销 / 运营 各自独立入口，核心字段齐全
- ContractFile：多附件（收款截图 / 合同扫描件 / PDF 电子合同），本地上传
"""
from django.db import models
from django.conf import settings
from apps.common.models import BaseModel


class ContractRecord(BaseModel):
    """合同订单（电销部 / 运营部 独立核算）"""
    DEPT = [
        ("SALES", "电销部"),
        ("OPS", "运营部"),
    ]
    STATUS = [
        ("PENDING", "待付款"), ("PAID", "已付款"),
        ("EXECUTING", "服务中"), ("FINISHED", "已完成"),
        ("CANCELED", "已作废"),
    ]

    dept = models.CharField("归属部门", max_length=20, choices=DEPT, default="SALES", db_index=True)
    company_name = models.CharField("企业名称", max_length=200)
    credit_code = models.CharField("企业税号(统一社会信用代码)", max_length=50, blank=True, default="")
    service_content = models.CharField("服务内容", max_length=200, help_text="如：公司注册 / 代理记账 / 注销")
    service_period = models.CharField("服务周期", max_length=50, blank=True, default="", help_text="如：2026-09 至 2027-08")
    amount = models.DecimalField("签单金额(元)", max_digits=14, decimal_places=2, default=0)
    signed_date = models.DateField("签单日期", null=True, blank=True)
    recv_account = models.CharField("收款账户", max_length=100, blank=True, default="", help_text="对公 / 对私收款账户")
    signer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="contract_records", verbose_name="签单人")
    customer_phone = models.CharField("客户联系电话", max_length=30, blank=True, default="")
    status = models.CharField("状态", max_length=20, choices=STATUS, default="PENDING")
    remark = models.TextField("备注", blank=True, default="")

    class Meta:
        verbose_name = "合同订单"
        verbose_name_plural = "合同订单"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_dept_display()}-{self.company_name}"


class ContractFile(BaseModel):
    """合同附件（多文件：收款截图 / 合同扫描件 / PDF 电子合同）"""
    FILE_TYPE = [
        ("RECEIPT", "收款截图"),
        ("SCAN", "合同扫描件"),
        ("PDF", "PDF电子合同"),
    ]
    record = models.ForeignKey(
        ContractRecord, on_delete=models.CASCADE, related_name="files", verbose_name="合同")
    file_type = models.CharField("附件类型", max_length=20, choices=FILE_TYPE, default="PDF")
    file = models.FileField("文件", upload_to="contracts/", max_length=500)

    class Meta:
        verbose_name = "合同附件"
        verbose_name_plural = "合同附件"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.record.company_name}-{self.get_file_type_display()}"
