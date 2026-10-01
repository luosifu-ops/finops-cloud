"""会计部：代账客户全做账流程"""
from django.db import models
from django.conf import settings
from apps.common.models import BaseModel


class TaxType(BaseModel):
    """税种与申报周期"""
    CYCLE = [("MONTH", "月报"), ("QUARTER", "季报"), ("YEAR", "年报"), ("IRREGULAR", "不定期")]
    name = models.CharField("税种名称", max_length=50,
                            help_text="增值税、企业所得税、个人所得税、附加税、印花税等")
    cycle = models.CharField("申报周期", max_length=20, choices=CYCLE, default="MONTH")
    deadline_rule = models.CharField("申报期限规则", max_length=100, blank=True,
                                     help_text="如：次月15日前")
    is_active = models.BooleanField("启用", default=True)

    class Meta:
        verbose_name = "税种"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.name}({self.get_cycle_display()})"


class AccountingClient(BaseModel):
    """代账客户档案（从成交客户转入）"""
    STATUS = [("ACTIVE", "正常服务"), ("PAUSED", "暂停"), ("STOPPED", "已终止"), ("TRANSFERRING", "交接中")]
    TAX_TYPE = [("GENERAL", "一般纳税人"), ("SMALL", "小规模纳税人"), ("INDIVIDUAL", "个体工商户")]
    customer = models.OneToOneField("sales.Customer", on_delete=models.CASCADE,
                                    related_name="accounting", verbose_name="客户")
    accountant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="acc_clients", verbose_name="主办会计")
    assistant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name="assist_clients", verbose_name="助理会计")
    taxpayer_type = models.CharField("纳税人类型", max_length=20, choices=TAX_TYPE, default="SMALL")
    tax_no = models.CharField("纳税人识别号", max_length=50, blank=True)
    tax_bureau = models.CharField("所属税局", max_length=100, blank=True)
    ele_tax_account = models.CharField("电子税务局账号", max_length=100, blank=True)
    ele_tax_password = models.CharField("电子税务局密码", max_length=100, blank=True)
    ukey_password = models.CharField("UK/税盘密码", max_length=100, blank=True)
    bank_account = models.CharField("基本户账号", max_length=60, blank=True)
    bank_name = models.CharField("开户行", max_length=100, blank=True)
    social_no = models.CharField("社保编号", max_length=60, blank=True)
    status = models.CharField("服务状态", max_length=20, choices=STATUS, default="ACTIVE")
    service_start = models.DateField("服务开始", null=True, blank=True)
    service_end = models.DateField("服务到期", null=True, blank=True)
    monthly_fee = models.DecimalField("月服务费", max_digits=12, decimal_places=2, default=0)
    zero_declare = models.BooleanField("零申报", default=False)
    remark = models.TextField("备注", blank=True)

    class Meta:
        verbose_name = "代账客户"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer.name}"


class MonthlyTask(BaseModel):
    """月度做账任务（每客户每月一条）"""
    STATUS = [
        ("WAIT_DOC", "待收资料"), ("DOING", "做账中"), ("WAIT_CONFIRM", "待客户确认"),
        ("DECLARED", "已申报"), ("DONE", "已完成"), ("DELAYED", "逾期"), ("SUSPENDED", "暂停"),
    ]
    client = models.ForeignKey(AccountingClient, on_delete=models.CASCADE, related_name="monthly_tasks",
                               verbose_name="客户")
    period = models.CharField("所属期间", max_length=7, db_index=True, help_text="如 2026-08")
    accountant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="acc_tasks", verbose_name="主办会计")
    status = models.CharField("状态", max_length=20, choices=STATUS, default="WAIT_DOC")
    doc_received_at = models.DateField("资料收到日", null=True, blank=True)
    voucher_done_at = models.DateField("做账完成日", null=True, blank=True)
    declared_at = models.DateField("申报完成日", null=True, blank=True)
    deadline = models.DateField("申报截止日", null=True, blank=True)
    is_overdue = models.BooleanField("是否逾期", default=False)
    income = models.DecimalField("本期收入", max_digits=14, decimal_places=2, default=0)
    cost = models.DecimalField("本期成本费用", max_digits=14, decimal_places=2, default=0)
    profit = models.DecimalField("本期利润", max_digits=14, decimal_places=2, default=0)
    vat_amount = models.DecimalField("增值税额", max_digits=12, decimal_places=2, default=0)
    surtax_amount = models.DecimalField("附加税额", max_digits=12, decimal_places=2, default=0)
    cit_amount = models.DecimalField("企业所得税额", max_digits=12, decimal_places=2, default=0)
    iit_amount = models.DecimalField("个税额", max_digits=12, decimal_places=2, default=0)
    stamp_amount = models.DecimalField("印花税额", max_digits=12, decimal_places=2, default=0)
    total_tax = models.DecimalField("合计税额", max_digits=12, decimal_places=2, default=0)
    zero_declare = models.BooleanField("零申报", default=False)
    remark = models.TextField("备注", blank=True)

    class Meta:
        verbose_name = "月度做账任务"
        verbose_name_plural = verbose_name
        unique_together = ("client", "period")
        ordering = ["-period", "client"]

    def __str__(self):
        return f"{self.client}-{self.period}"


class TaskStep(BaseModel):
    """做账流程节点（收票→整理→做账→审核→申报→归档）"""
    STEP = [
        ("COLLECT", "收集票据"), ("SORT", "整理录入"), ("VOUCHER", "编制凭证"),
        ("REVIEW", "主管审核"), ("DECLARE", "税务申报"), ("FEEDBACK", "客户反馈"), ("ARCHIVE", "归档"),
    ]
    STATUS = [("TODO", "待办"), ("DOING", "进行中"), ("DONE", "已完成"), ("BLOCKED", "受阻")]
    task = models.ForeignKey(MonthlyTask, on_delete=models.CASCADE, related_name="steps", verbose_name="月度任务")
    step = models.CharField("节点", max_length=20, choices=STEP, default="COLLECT")
    status = models.CharField("状态", max_length=20, choices=STATUS, default="TODO")
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="acc_steps", verbose_name="处理人")
    finished_at = models.DateTimeField("完成时间", null=True, blank=True)
    remark = models.CharField("备注", max_length=300, blank=True)

    class Meta:
        verbose_name = "做账节点"
        verbose_name_plural = verbose_name
        ordering = ["id"]
        unique_together = ("task", "step")


class Voucher(BaseModel):
    """记账凭证"""
    task = models.ForeignKey(MonthlyTask, on_delete=models.CASCADE, related_name="vouchers", verbose_name="月度任务")
    voucher_no = models.CharField("凭证号", max_length=30)
    date = models.DateField("业务日期", null=True, blank=True)
    summary = models.CharField("摘要", max_length=200, blank=True)
    subject = models.CharField("会计科目", max_length=100, blank=True)
    debit = models.DecimalField("借方金额", max_digits=14, decimal_places=2, default=0)
    credit = models.DecimalField("贷方金额", max_digits=14, decimal_places=2, default=0)
    attachment_count = models.IntegerField("附件张数", default=0)
    made_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="made_vouchers", verbose_name="制单人")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="reviewed_vouchers", verbose_name="审核人")

    class Meta:
        verbose_name = "记账凭证"
        verbose_name_plural = verbose_name
        ordering = ["voucher_no"]


class Invoice(BaseModel):
    """发票管理（进项 / 销项）"""
    DIRECTION = [("INPUT", "进项"), ("OUTPUT", "销项")]
    KIND = [("SPECIAL", "增值税专用发票"), ("GENERAL", "增值税普通发票"),
            ("ELEC", "电子发票"), ("QUOTA", "定额发票"), ("OTHER", "其他")]
    STATUS = [("UNUSED", "未认证"), ("CERTIFIED", "已认证"), ("DEDUCTED", "已抵扣"),
              ("VOID", "已作废"), ("RED", "已红冲")]
    task = models.ForeignKey(MonthlyTask, on_delete=models.CASCADE, related_name="invoices",
                             null=True, blank=True, verbose_name="月度任务")
    client = models.ForeignKey(AccountingClient, on_delete=models.CASCADE, related_name="invoices", verbose_name="客户")
    direction = models.CharField("进/销项", max_length=20, choices=DIRECTION, default="INPUT")
    kind = models.CharField("发票类型", max_length=20, choices=KIND, default="GENERAL")
    code = models.CharField("发票代码", max_length=30, blank=True)
    number = models.CharField("发票号码", max_length=30, blank=True)
    invoice_date = models.DateField("开票日期", null=True, blank=True)
    seller = models.CharField("销售方", max_length=200, blank=True)
    buyer = models.CharField("购买方", max_length=200, blank=True)
    amount_ex_tax = models.DecimalField("不含税金额", max_digits=14, decimal_places=2, default=0)
    tax = models.DecimalField("税额", max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField("价税合计", max_digits=14, decimal_places=2, default=0)
    tax_rate = models.DecimalField("税率(%)", max_digits=6, decimal_places=2, default=0)
    status = models.CharField("状态", max_length=20, choices=STATUS, default="UNUSED")
    file = models.FileField("发票影像", upload_to="invoice/", null=True, blank=True)

    class Meta:
        verbose_name = "发票"
        verbose_name_plural = verbose_name
        ordering = ["-invoice_date"]


class BankStatement(BaseModel):
    """银行流水"""
    client = models.ForeignKey(AccountingClient, on_delete=models.CASCADE, related_name="bank_statements",
                               verbose_name="客户")
    task = models.ForeignKey(MonthlyTask, on_delete=models.CASCADE, related_name="bank_statements",
                             null=True, blank=True, verbose_name="月度任务")
    trans_date = models.DateField("交易日期", null=True, blank=True)
    summary = models.CharField("摘要", max_length=200, blank=True)
    counterparty = models.CharField("对方户名", max_length=200, blank=True)
    income = models.DecimalField("收入", max_digits=14, decimal_places=2, default=0)
    expense = models.DecimalField("支出", max_digits=14, decimal_places=2, default=0)
    balance = models.DecimalField("余额", max_digits=14, decimal_places=2, default=0)
    file = models.FileField("流水附件", upload_to="bank/", null=True, blank=True)

    class Meta:
        verbose_name = "银行流水"
        verbose_name_plural = verbose_name
        ordering = ["-trans_date"]


class TaxDeclaration(BaseModel):
    """纳税申报记录"""
    STATUS = [("PENDING", "待申报"), ("DECLARED", "已申报"), ("PAID", "已缴税"), ("OVERDUE", "逾期"), ("ZERO", "零申报")]
    task = models.ForeignKey(MonthlyTask, on_delete=models.CASCADE, related_name="declarations", verbose_name="月度任务")
    tax_type = models.ForeignKey(TaxType, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="税种")
    period = models.CharField("税款所属期", max_length=20, blank=True)
    deadline = models.DateField("申报截止日", null=True, blank=True)
    declared_at = models.DateTimeField("申报时间", null=True, blank=True)
    amount = models.DecimalField("申报税额", max_digits=12, decimal_places=2, default=0)
    paid_amount = models.DecimalField("已缴税额", max_digits=12, decimal_places=2, default=0)
    status = models.CharField("状态", max_length=20, choices=STATUS, default="PENDING")
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="declarations", verbose_name="申报人")
    screenshot = models.ImageField("申报截图", upload_to="declare/", null=True, blank=True)
    remark = models.CharField("备注", max_length=300, blank=True)

    class Meta:
        verbose_name = "纳税申报"
        verbose_name_plural = verbose_name
        ordering = ["-deadline"]


class SocialInsurance(BaseModel):
    """社保公积金申报"""
    client = models.ForeignKey(AccountingClient, on_delete=models.CASCADE, related_name="social_records",
                               verbose_name="客户")
    month = models.CharField("所属月份", max_length=7, db_index=True)
    person_count = models.IntegerField("参保人数", default=0)
    base_total = models.DecimalField("缴费基数合计", max_digits=14, decimal_places=2, default=0)
    company_amount = models.DecimalField("单位缴纳", max_digits=12, decimal_places=2, default=0)
    personal_amount = models.DecimalField("个人缴纳", max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField("合计", max_digits=12, decimal_places=2, default=0)
    declared = models.BooleanField("已申报", default=False)
    declared_at = models.DateTimeField("申报时间", null=True, blank=True)

    class Meta:
        verbose_name = "社保公积金"
        verbose_name_plural = verbose_name
        unique_together = ("client", "month")
        ordering = ["-month"]


class AnnualReport(BaseModel):
    """工商年报"""
    client = models.ForeignKey(AccountingClient, on_delete=models.CASCADE, related_name="annual_reports",
                               verbose_name="客户")
    year = models.IntegerField("年报年度", db_index=True)
    deadline = models.DateField("截止日期", null=True, blank=True)
    submitted = models.BooleanField("已报送", default=False)
    submitted_at = models.DateTimeField("报送时间", null=True, blank=True)
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="annual_reports", verbose_name="经办人")

    class Meta:
        verbose_name = "工商年报"
        verbose_name_plural = verbose_name
        unique_together = ("client", "year")
        ordering = ["-year"]


class BusinessItem(BaseModel):
    """工商事项：注册 / 变更 / 注销 / 异常处理"""
    ITEM_TYPE = [
        ("REGISTER", "公司注册"), ("CHANGE", "工商变更"), ("CANCEL", "公司注销"),
        ("ABNORMAL", "异常处理"), ("ADDRESS", "地址挂靠"), ("LICENSE", "执照补办"),
        ("BRANCH", "分公司设立"), ("OTHER", "其他"),
    ]
    STATUS = [("PENDING", "待办理"), ("PROCESSING", "办理中"), ("DONE", "已完成"),
              ("REJECTED", "被驳回"), ("CANCELED", "已取消")]
    client = models.ForeignKey(AccountingClient, on_delete=models.CASCADE, related_name="business_items",
                               null=True, blank=True, verbose_name="客户")
    title = models.CharField("事项名称", max_length=200)
    item_type = models.CharField("事项类型", max_length=20, choices=ITEM_TYPE, default="OTHER")
    status = models.CharField("状态", max_length=20, choices=STATUS, default="PENDING")
    handler = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="business_items", verbose_name="经办人")
    start_at = models.DateField("开始日期", null=True, blank=True)
    due_at = models.DateField("承诺完成日", null=True, blank=True)
    finished_at = models.DateField("实际完成日", null=True, blank=True)
    progress = models.IntegerField("进度(%)", default=0)
    fee = models.DecimalField("费用", max_digits=12, decimal_places=2, default=0)
    result = models.TextField("办理结果", blank=True)
    remark = models.TextField("备注", blank=True)

    class Meta:
        verbose_name = "工商事项"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]


class ClientDocument(BaseModel):
    """客户资料 / 证件管理"""
    KIND = [
        ("LICENSE", "营业执照"), ("ID_CARD", "法人身份证"), ("BANK", "银行账户资料"),
        ("TAX", "税务资料"), ("SEAL", "印章信息"), ("CONTRACT", "合同协议"),
        ("CERT", "资质证书"), ("OTHER", "其他"),
    ]
    client = models.ForeignKey(AccountingClient, on_delete=models.CASCADE, related_name="documents", verbose_name="客户")
    name = models.CharField("资料名称", max_length=200)
    kind = models.CharField("资料类型", max_length=20, choices=KIND, default="OTHER")
    file = models.FileField("文件", upload_to="documents/", null=True, blank=True)
    expire_at = models.DateField("有效期至", null=True, blank=True)
    version = models.CharField("版本", max_length=20, blank=True)
    remark = models.CharField("备注", max_length=300, blank=True)

    class Meta:
        verbose_name = "客户资料"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]


class HandoverRecord(BaseModel):
    """客户交接记录（会计离职/调岗时的交接）"""
    client = models.ForeignKey(AccountingClient, on_delete=models.CASCADE, related_name="handovers", verbose_name="客户")
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                  related_name="handover_out", verbose_name="移交人")
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                related_name="handover_in", verbose_name="接收人")
    reason = models.CharField("交接原因", max_length=200, blank=True)
    checklist = models.JSONField("交接清单", default=list, blank=True,
                                 help_text='[{"item":"凭证","done":true}]')
    confirmed = models.BooleanField("已确认", default=False)
    confirmed_at = models.DateTimeField("确认时间", null=True, blank=True)

    class Meta:
        verbose_name = "交接记录"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
