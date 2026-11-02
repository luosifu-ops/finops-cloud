"""电销部：线索 / 客户 / 跟进 / 通话 / 合同 / 业绩"""
from django.db import models
from django.conf import settings
from apps.common.models import BaseModel


class Lead(BaseModel):
    # 自动编号：线索单号
    AUTO_NO_FIELDS = {"lead_no": "LD"}
    """销售线索（运营部投放进来，分配给电销）"""
    SOURCE = [
        ("AMAP", "高德"), ("BAIDU", "百度"), ("XIAOHONGSHU", "小红书"),
        ("DOUYIN", "抖音"), ("KUAISHOU", "快手"), ("WECHAT", "微信"),
        ("REFERRAL", "转介绍"), ("OFFLINE", "线下"), ("OTHER", "其他"),
    ]
    STATUS = [
        ("NEW", "待分配"), ("ASSIGNED", "已分配"), ("FOLLOWING", "跟进中"),
        ("INTENTION", "高意向"), ("DEAL", "已成交"), ("LOST", "已流失"), ("INVALID", "无效"),
    ]
    name = models.CharField("客户姓名", max_length=50)
    phone = models.CharField("联系电话", max_length=30, db_index=True)
    wechat = models.CharField("微信", max_length=60, blank=True)
    company = models.CharField("公司名称", max_length=200, blank=True)
    source = models.CharField("来源渠道", max_length=20, choices=SOURCE, default="OTHER")
    source_detail = models.CharField("渠道明细(计划/账户)", max_length=100, blank=True)
    intention = models.CharField("意向业务", max_length=100, blank=True,
                                 help_text="如：注册公司、代理记账、注销")
    level = models.CharField("意向等级", max_length=10,
                             choices=[("A", "A级"), ("B", "B级"), ("C", "C级"), ("D", "D级")], default="C")
    status = models.CharField("状态", max_length=20, choices=STATUS, default="NEW")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name="leads", verbose_name="归属销售")
    # 分配人（电销主管/组长等将线索分配给归属销售时记录），用于主管可编辑其分配出去的内容
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="assigned_leads", verbose_name="分配人")
    ops_record = models.ForeignKey("ops.AdDailyStat", on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="leads", verbose_name="关联投放数据")
    remark = models.TextField("备注", blank=True)
    lost_reason = models.CharField("流失原因", max_length=300, blank=True)
    assigned_at = models.DateTimeField("分配时间", null=True, blank=True)
    dealt_at = models.DateTimeField("成交时间", null=True, blank=True)
    # 线索单号（系统自动生成，无需手填）
    lead_no = models.CharField("线索单号", max_length=32, blank=True, db_index=True,
                               help_text="线索系统编号，由系统自动生成")

    class Meta:
        verbose_name = "销售线索"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name}-{self.phone}"


class Customer(BaseModel):
    """成交客户档案"""
    TYPE = [("ENTERPRISE", "企业"), ("INDIVIDUAL", "个体工商户"), ("PERSONAL", "个人")]
    name = models.CharField("客户名称", max_length=200)
    short_name = models.CharField("简称", max_length=100, blank=True)
    customer_type = models.CharField("客户类型", max_length=20, choices=TYPE, default="ENTERPRISE")
    contact = models.CharField("联系人", max_length=50, blank=True)
    phone = models.CharField("联系电话", max_length=30, blank=True, db_index=True)
    wechat = models.CharField("微信", max_length=60, blank=True)
    credit_code = models.CharField("统一社会信用代码", max_length=50, blank=True)
    industry = models.CharField("所属行业", max_length=100, blank=True)
    region = models.CharField("所属区域", max_length=100, blank=True)
    address = models.CharField("地址", max_length=300, blank=True)
    source = models.CharField("来源渠道", max_length=20, default="OTHER")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name="customers", verbose_name="归属销售")
    accountant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="accounting_customers", verbose_name="主办会计")
    level = models.CharField("客户等级", max_length=10, default="C")
    status = models.CharField("状态", max_length=20,
                              choices=[("COOPERATING", "合作中"), ("PAUSED", "暂停"), ("CHURNED", "已流失")],
                              default="COOPERATING")
    signed_at = models.DateField("签约日期", null=True, blank=True)
    expire_at = models.DateField("服务到期日", null=True, blank=True)
    # 客户标签（2026-10-29 Boss 专项：客户档案标签分级）：多对多，标签可增删改配色
    tags = models.ManyToManyField("sales.CustomerTag", blank=True, related_name="customers",
                                  verbose_name="客户标签")
    remark = models.TextField("备注", blank=True)

    class Meta:
        verbose_name = "客户档案"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class Contract(BaseModel):
    # 自动编号：合同编号
    AUTO_NO_FIELDS = {"contract_no": "HT"}
    """合同/订单"""
    BIZ_TYPE = [
        ("REGISTER", "公司注册"), ("AGENCY", "代理记账"), ("TAX", "税务申报"),
        ("CHANGE", "工商变更"), ("CANCEL", "公司注销"), ("ADDRESS", "地址挂靠"),
        ("SOCIAL", "社保代理"), ("AUDIT", "审计验资"), ("OTHER", "其他"),
    ]
    STATUS = [("PENDING", "待付款"), ("PAID", "已付款"), ("EXECUTING", "服务中"),
              ("FINISHED", "已完成"), ("REFUNDED", "已退款"), ("CANCELED", "已作废")]
    PAY_TYPE = [("FULL", "全款"), ("DEPOSIT", "定金+尾款"), ("INSTALLMENT", "分期"), ("MONTHLY", "月付")]

    contract_no = models.CharField("合同编号", max_length=50, unique=True, blank=True,
                                        help_text="系统自动生成，亦可手填（需保证唯一）")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="contracts", verbose_name="客户")
    lead = models.ForeignKey(Lead, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name="contracts", verbose_name="来源线索")
    biz_type = models.CharField("业务类型", max_length=20, choices=BIZ_TYPE, default="AGENCY")
    title = models.CharField("合同标题", max_length=200)
    amount = models.DecimalField("合同金额", max_digits=14, decimal_places=2, default=0)
    received = models.DecimalField("已收金额", max_digits=14, decimal_places=2, default=0)
    pay_type = models.CharField("付款方式", max_length=20, choices=PAY_TYPE, default="FULL")
    service_period = models.CharField("服务周期", max_length=50, blank=True, help_text="如：2026-09至2027-08")
    sales = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name="contracts", verbose_name="签单销售")
    # 分配人（运营主管/组长等将合同指派给签单销售时记录），用于主管可编辑其分配出去的单据
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="assigned_contracts", verbose_name="分配人")
    status = models.CharField("状态", max_length=20, choices=STATUS, default="PENDING")
    signed_date = models.DateField("签订日期", null=True, blank=True)
    start_date = models.DateField("服务开始", null=True, blank=True)
    end_date = models.DateField("服务结束", null=True, blank=True)
    attachment = models.FileField("合同扫描件", upload_to="contract/", null=True, blank=True)
    # 客户付款截图（增量功能：合同管理内上传客户付款凭证）
    payment_screenshot = models.FileField("客户付款截图", upload_to="contract/payment/", null=True, blank=True)
    remark = models.TextField("备注", blank=True)

    class Meta:
        verbose_name = "合同订单"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.contract_no}-{self.customer.name}"

    @property
    def receivable(self):
        return self.amount - self.received


class CallRecord(models.Model):
    """通话记录"""
    RESULT = [("CONNECTED", "已接通"), ("NO_ANSWER", "未接"), ("REJECTED", "拒接"),
              ("SHUTDOWN", "关机/停机"), ("WRONG", "空号/错号")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="call_records", verbose_name="通话人")
    lead = models.ForeignKey(Lead, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name="calls", verbose_name="关联线索")
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="calls", verbose_name="关联客户")
    phone = models.CharField("号码", max_length=30, blank=True)
    duration = models.IntegerField("通话时长(秒)", default=0)
    result = models.CharField("通话结果", max_length=20, choices=RESULT, default="CONNECTED")
    has_wechat = models.BooleanField("是否加微", default=False)
    summary = models.TextField("沟通要点", blank=True)
    created_at = models.DateTimeField("通话时间", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "通话记录"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]


class FollowUp(BaseModel):
    """跟进记录"""
    WAY = [("PHONE", "电话"), ("WECHAT", "微信"), ("VISIT", "上门"), ("MEETING", "会议"), ("OTHER", "其他")]
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="followups",
                             null=True, blank=True, verbose_name="线索")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="followups",
                                 null=True, blank=True, verbose_name="客户")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="followups", verbose_name="跟进人")
    way = models.CharField("跟进方式", max_length=20, choices=WAY, default="PHONE")
    content = models.TextField("跟进内容")
    next_at = models.DateTimeField("下次跟进时间", null=True, blank=True)
    next_action = models.CharField("下一步动作", max_length=200, blank=True)

    class Meta:
        verbose_name = "跟进记录"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]


class SalesTarget(BaseModel):
    """业绩目标（按月，可下达到部门/小组/个人）"""
    SCOPE = [("COMPANY", "公司"), ("DEPARTMENT", "部门"), ("TEAM", "小组"), ("PERSON", "个人")]
    month = models.CharField("月份", max_length=7, db_index=True)
    scope = models.CharField("范围", max_length=20, choices=SCOPE, default="PERSON")
    department = models.ForeignKey("accounts.Department", on_delete=models.CASCADE,
                                   null=True, blank=True, related_name="targets", verbose_name="部门")
    team = models.ForeignKey("accounts.Team", on_delete=models.CASCADE,
                             null=True, blank=True, related_name="targets", verbose_name="小组")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             null=True, blank=True, related_name="targets", verbose_name="员工")
    amount_target = models.DecimalField("业绩目标(元)", max_digits=14, decimal_places=2, default=0)
    order_target = models.IntegerField("订单数目标", default=0)
    call_target = models.IntegerField("通话量目标", default=0)

    class Meta:
        verbose_name = "业绩目标"
        verbose_name_plural = verbose_name
        ordering = ["-month"]


class CommissionRule(BaseModel):
    """提成规则"""
    RULE_TYPE = [("RATE", "按金额比例"), ("FIXED", "按单固定"), ("LADDER", "阶梯提成")]
    name = models.CharField("规则名称", max_length=100)
    rule_type = models.CharField("规则类型", max_length=20, choices=RULE_TYPE, default="RATE")
    department = models.ForeignKey("accounts.Department", on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name="适用部门")
    rate = models.DecimalField("提成比例(%)", max_digits=6, decimal_places=2, default=0)
    fixed_amount = models.DecimalField("固定金额(元/单)", max_digits=10, decimal_places=2, default=0)
    ladder = models.JSONField("阶梯配置", default=list, blank=True,
                              help_text='[{"min":0,"max":50000,"rate":5},{"min":50000,"max":100000,"rate":8}]')
    effective_month = models.CharField("生效月份", max_length=7, default="2026-09")
    remark = models.CharField("说明", max_length=300, blank=True)

    class Meta:
        verbose_name = "提成规则"
        verbose_name_plural = verbose_name


class Streamer(BaseModel):
    """主播（直播获客/带货）：归属部门与负责人，记录粉丝、开播、GMV、提成"""
    PLATFORM = [
        ("DOUYIN", "抖音"), ("KUAISHOU", "快手"),
        ("VIDEO", "视频号"), ("RED", "小红书"), ("OTHER", "其他"),
    ]
    STATUS = [
        ("ACTIVE", "开播中"), ("INACTIVE", "停播"), ("RESIGNED", "已离职"),
    ]
    name = models.CharField("主播昵称/姓名", max_length=50)
    real_name = models.CharField("真实姓名", max_length=50, blank=True)
    platform = models.CharField("直播平台", max_length=20, choices=PLATFORM, default="DOUYIN")
    account = models.CharField("账号/主页ID", max_length=120, blank=True)
    phone = models.CharField("联系电话", max_length=30, blank=True)
    department = models.ForeignKey(
        "accounts.Department", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="streamers", verbose_name="所属部门")
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="managed_streamers", verbose_name="负责人")
    status = models.CharField("状态", max_length=20, choices=STATUS, default="ACTIVE")
    entry_date = models.DateField("入职日期", null=True, blank=True)
    fans_count = models.IntegerField("粉丝数", default=0)
    live_count = models.IntegerField("本月开播场次", default=0)
    gmv = models.DecimalField("本月GMV(元)", max_digits=14, decimal_places=2, default=0)
    commission_rate = models.DecimalField("提成比例(%)", max_digits=6, decimal_places=2, default=0)
    remark = models.TextField("备注", blank=True)

    class Meta:
        verbose_name = "主播"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name}（{self.get_platform_display()}）"


class SalaryRecord(BaseModel):
    """工资核算记录：输入业绩 → 自动核算底薪+提成+奖金-扣款=实发"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="salary_records", verbose_name="员工")
    month = models.CharField("核算月份", max_length=7, db_index=True)
    base_salary = models.DecimalField("底薪", max_digits=12, decimal_places=2, default=0)
    performance = models.DecimalField("业绩(元)", max_digits=14, decimal_places=2, default=0,
                                      help_text="本月签单业绩")
    commission = models.DecimalField("提成(元)", max_digits=12, decimal_places=2, default=0)
    commission_rule = models.CharField("适用提成规则", max_length=100, blank=True)
    bonus = models.DecimalField("奖金(元)", max_digits=12, decimal_places=2, default=0,
                                help_text="全勤奖/达标奖等")
    deduction = models.DecimalField("扣款(元)", max_digits=12, decimal_places=2, default=0,
                                    help_text="迟到/请假/社保个人部分等")
    total = models.DecimalField("实发工资(元)", max_digits=14, decimal_places=2, default=0)
    settled = models.BooleanField("是否已发放", default=False)
    remark = models.TextField("备注", blank=True)

    class Meta:
        verbose_name = "工资核算"
        verbose_name_plural = verbose_name
        ordering = ["-month", "user"]
        unique_together = [("user", "month")]

    def __str__(self):
        return f"{self.user.display_name}-{self.month}"


class CustomerTag(BaseModel):
    """客户标签（2026-10-29 Boss 专项：客户档案标签分级）

    用于客户分层运营：如「重点客户/高意向/待续费/需催款/转介绍来源」等，
    支持自定义配色，前端以彩色标签展示并可按标签筛选。
    """
    name = models.CharField("标签名称", max_length=30, unique=True)
    color = models.CharField("标签颜色", max_length=20, default="primary",
                             help_text="前端标签配色：primary/success/warning/danger/info")
    sort = models.IntegerField("排序", default=0)
    is_active = models.BooleanField("启用", default=True)
    remark = models.CharField("说明", max_length=200, blank=True)

    class Meta:
        verbose_name = "客户标签"
        verbose_name_plural = verbose_name
        ordering = ["sort", "id"]

    def __str__(self):
        return self.name
