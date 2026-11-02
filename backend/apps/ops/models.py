"""运营部：多平台投放 / 内容运营 / 引流转化"""
from django.db import models
from django.conf import settings
from apps.common.models import BaseModel


class AdPlatform(BaseModel):
    """投放平台：高德、百度、小红书、抖音等"""
    CODE = [
        ("AMAP", "高德地图"), ("BAIDU", "百度推广"), ("XIAOHONGSHU", "小红书"),
        ("DOUYIN", "抖音"), ("KUAISHOU", "快手"), ("WECHAT", "微信广告"),
        ("TENCENT", "腾讯广告"), ("360", "360搜索"), ("OFFLINE", "线下地推"), ("OTHER", "其他"),
    ]
    name = models.CharField("平台名称", max_length=50)
    code = models.CharField("平台编码", max_length=20, choices=CODE, unique=True)
    login_url = models.CharField("后台地址", max_length=300, blank=True)
    account_name = models.CharField("账户名", max_length=100, blank=True)
    contact = models.CharField("对接人/渠道经理", max_length=50, blank=True)
    contact_phone = models.CharField("联系电话", max_length=30, blank=True)
    has_api = models.BooleanField("支持API自动拉取", default=False)
    remark = models.TextField("备注", blank=True)

    class Meta:
        verbose_name = "投放平台"
        verbose_name_plural = verbose_name
        ordering = ["id"]

    def __str__(self):
        return self.name


class AdAccount(BaseModel):
    """广告账户（一个平台可有多个账户）"""
    platform = models.ForeignKey(AdPlatform, on_delete=models.CASCADE, related_name="accounts", verbose_name="平台")
    name = models.CharField("账户名称", max_length=100)
    account_id = models.CharField("平台账户ID", max_length=100, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name="ad_accounts", verbose_name="负责人")
    daily_budget = models.DecimalField("日预算", max_digits=12, decimal_places=2, default=0)
    month_budget = models.DecimalField("月预算", max_digits=12, decimal_places=2, default=0)
    balance = models.DecimalField("账户余额", max_digits=12, decimal_places=2, default=0)
    status = models.CharField("状态", max_length=20,
                              choices=[("ACTIVE", "投放中"), ("PAUSED", "已暂停"), ("CLOSED", "已停用")],
                              default="ACTIVE")

    class Meta:
        verbose_name = "广告账户"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.platform.name}-{self.name}"


class AdCampaign(BaseModel):
    """推广计划/项目"""
    account = models.ForeignKey(AdAccount, on_delete=models.CASCADE, related_name="campaigns", verbose_name="广告账户")
    name = models.CharField("计划名称", max_length=100)
    campaign_id = models.CharField("平台计划ID", max_length=100, blank=True)
    goal = models.CharField("推广目标", max_length=50, default="线索",
                            help_text="如：线索/表单/私信/到店")
    biz_line = models.CharField("业务线", max_length=50, blank=True,
                                help_text="如：公司注册、代理记账")
    city = models.CharField("投放城市", max_length=50, blank=True)
    start_date = models.DateField("开始日期", null=True, blank=True)
    end_date = models.DateField("结束日期", null=True, blank=True)
    status = models.CharField("状态", max_length=20, default="ACTIVE")

    class Meta:
        verbose_name = "推广计划"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class AdDailyStat(models.Model):
    """每日投放数据（手动录入 / 表格导入 / 未来接API）"""
    platform = models.ForeignKey(AdPlatform, on_delete=models.CASCADE, related_name="daily_stats", verbose_name="平台")
    account = models.ForeignKey(AdAccount, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="daily_stats", verbose_name="账户")
    campaign = models.ForeignKey(AdCampaign, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="daily_stats", verbose_name="计划")
    date = models.DateField("日期", db_index=True)

    cost = models.DecimalField("消耗(元)", max_digits=12, decimal_places=2, default=0)
    impression = models.IntegerField("展现量", default=0)
    click = models.IntegerField("点击量", default=0)
    click_rate = models.DecimalField("点击率(%)", max_digits=6, decimal_places=2, default=0)
    avg_click_cost = models.DecimalField("平均点击成本", max_digits=10, decimal_places=2, default=0)

    lead_count = models.IntegerField("留资线索数", default=0)
    valid_lead = models.IntegerField("有效线索数", default=0)
    phone_added = models.IntegerField("电话数", default=0)
    wechat_added = models.IntegerField("加微数", default=0)
    visit_count = models.IntegerField("到店/邀约数", default=0)
    deal_count = models.IntegerField("成交数", default=0)
    deal_amount = models.DecimalField("成交金额", max_digits=14, decimal_places=2, default=0)

    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="ad_stats", verbose_name="录入人")
    remark = models.CharField("备注", max_length=300, blank=True)
    created_at = models.DateTimeField("录入时间", auto_now_add=True)

    class Meta:
        verbose_name = "投放日报"
        verbose_name_plural = verbose_name
        unique_together = ("platform", "account", "campaign", "date")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.platform.name}-{self.date}"

    @property
    def cpl(self):
        """线索成本 = 消耗 / 线索数"""
        if self.lead_count:
            return round(float(self.cost) / self.lead_count, 2)
        return 0

    @property
    def cac(self):
        """获客成本 = 消耗 / 成交数"""
        if self.deal_count:
            return round(float(self.cost) / self.deal_count, 2)
        return 0

    @property
    def roi(self):
        """投产比 = 成交金额 / 消耗"""
        if self.cost and float(self.cost) > 0:
            return round(float(self.deal_amount) / float(self.cost), 2)
        return 0

    @property
    def lead_valid_rate(self):
        if self.lead_count:
            return round(self.valid_lead / self.lead_count * 100, 1)
        return 0


class AdCreative(BaseModel):
    """投放素材"""
    KIND = [("IMAGE", "图片"), ("VIDEO", "视频"), ("TEXT", "文案"), ("LP", "落地页")]
    platform = models.ForeignKey(AdPlatform, on_delete=models.CASCADE, related_name="creatives", verbose_name="平台")
    name = models.CharField("素材名称", max_length=100)
    kind = models.CharField("素材类型", max_length=20, choices=KIND, default="IMAGE")
    file = models.FileField("素材文件", upload_to="creative/", null=True, blank=True)
    copy = models.TextField("文案", blank=True)
    link = models.CharField("落地页链接", max_length=300, blank=True)
    cost = models.DecimalField("关联消耗", max_digits=12, decimal_places=2, default=0)
    lead_count = models.IntegerField("带来线索", default=0)
    impression = models.IntegerField("展现量", default=0)
    online = models.BooleanField("投放中", default=True)

    class Meta:
        verbose_name = "投放素材"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]


class ContentPost(BaseModel):
    """内容发布（小红书笔记 / 抖音视频 / 公众号文章）"""
    KIND = [("NOTE", "图文笔记"), ("VIDEO", "短视频"), ("ARTICLE", "长文"), ("LIVE", "直播")]
    platform = models.CharField("平台", max_length=20,
                                choices=[("XIAOHONGSHU", "小红书"), ("DOUYIN", "抖音"),
                                         ("KUAISHOU", "快手"), ("WECHAT", "公众号"),
                                         ("VIDEO_ACCOUNT", "视频号"), ("BAIDU", "百度")],
                                default="XIAOHONGSHU")
    kind = models.CharField("内容形式", max_length=20, choices=KIND, default="NOTE")
    title = models.CharField("标题", max_length=200)
    topic = models.CharField("选题/话题", max_length=100, blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name="content_posts", verbose_name="产出人")
    publish_at = models.DateTimeField("发布时间", null=True, blank=True)
    link = models.CharField("内容链接", max_length=300, blank=True)
    cover = models.ImageField("封面", upload_to="content/", null=True, blank=True)
    script = models.TextField("脚本/正文", blank=True)
    status = models.CharField("状态", max_length=20,
                              choices=[("IDEA", "选题中"), ("PRODUCING", "制作中"),
                                       ("PUBLISHED", "已发布"), ("OFFLINE", "已下架")], default="IDEA")

    class Meta:
        verbose_name = "内容作品"
        verbose_name_plural = verbose_name
        ordering = ["-publish_at", "-created_at"]

    def __str__(self):
        return self.title


class ContentStat(models.Model):
    """内容数据（发布后 1/3/7 天跟踪）"""
    post = models.ForeignKey(ContentPost, on_delete=models.CASCADE, related_name="stats", verbose_name="内容")
    stat_date = models.DateField("统计日期")
    view = models.IntegerField("播放/阅读", default=0)
    like = models.IntegerField("点赞", default=0)
    comment = models.IntegerField("评论", default=0)
    share = models.IntegerField("转发", default=0)
    collect = models.IntegerField("收藏", default=0)
    follow = models.IntegerField("涨粉", default=0)
    private_msg = models.IntegerField("私信数", default=0)
    lead_count = models.IntegerField("留资数", default=0)

    class Meta:
        verbose_name = "内容数据"
        verbose_name_plural = verbose_name
        unique_together = ("post", "stat_date")
        ordering = ["-stat_date"]


class ChannelBudget(BaseModel):
    """渠道预算与规划"""
    month = models.CharField("月份", max_length=7, db_index=True)
    platform = models.ForeignKey(AdPlatform, on_delete=models.CASCADE, related_name="budgets", verbose_name="平台")
    budget = models.DecimalField("预算(元)", max_digits=12, decimal_places=2, default=0)
    lead_target = models.IntegerField("线索目标", default=0)
    deal_target = models.IntegerField("成交目标", default=0)
    remark = models.CharField("备注", max_length=300, blank=True)
    # —— 预算审批（与迁移 0002_budget_approval 对齐）——
    approve_status = models.CharField("审批状态", max_length=20,
                                       choices=[("APPROVED", "已生效"), ("PENDING", "待审批"), ("REJECTED", "已驳回")],
                                       db_index=True, default="APPROVED")
    pending_budget = models.DecimalField("待审批预算", max_digits=12, decimal_places=2, null=True, blank=True)
    pending_reason = models.CharField("申请理由", max_length=300, blank=True)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name="approved_budgets", verbose_name="审批人")
    reviewed_at = models.DateTimeField("审批时间", null=True, blank=True)
    reject_reason = models.CharField("驳回理由", max_length=300, blank=True)

    class Meta:
        verbose_name = "渠道预算"
        verbose_name_plural = verbose_name
        unique_together = ("month", "platform")
        ordering = ["-month"]


class OpsDailyReport(BaseModel):
    """运营日报"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="ops_daily_reports", verbose_name="运营")
    date = models.DateField("日期", db_index=True)
    total_cost = models.DecimalField("总消耗", max_digits=12, decimal_places=2, default=0)
    total_lead = models.IntegerField("总线索", default=0)
    total_wechat = models.IntegerField("总加微", default=0)
    total_deal = models.IntegerField("总成交", default=0)
    highlights = models.TextField("今日亮点", blank=True)
    problems = models.TextField("问题", blank=True)
    tomorrow_plan = models.TextField("明日计划", blank=True)
    attachments = models.JSONField("截图附件", default=list, blank=True)

    class Meta:
        verbose_name = "运营日报"
        verbose_name_plural = verbose_name
        unique_together = ("user", "date")
        ordering = ["-date"]


# ============== 主播板块：获客日报 / 留资台账 / 直播投流 ==============

class AnchorDailyReport(BaseModel):
    """主播获客日报：五大板块（渠道付费投放/直播获客/本地推投流/AI获客/视频号小红书闲鱼获客）。
    直播板块额外含直播专属字段；进房率/获客成本/留资成本自动计算。"""
    CHANNEL = [
        ("PAID", "渠道获客-付费投放"),
        ("LIVE", "直播获客"),
        ("LOCAL_PUSH", "本地推投流获客"),
        ("AI", "AI获客"),
        ("SOCIAL", "视频号/小红书/闲鱼获客"),
    ]
    channel_type = models.CharField("获客板块", max_length=20, choices=CHANNEL, default="PAID", db_index=True)
    date = models.DateField("日期", db_index=True)
    anchor_name = models.CharField("主播/账号", max_length=100, blank=True)
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="anchor_daily_reports", verbose_name="跟进人/录入人")
    # 通用字段
    cost = models.DecimalField("消耗(元)", max_digits=12, decimal_places=2, default=0)
    lead_count = models.IntegerField("线索数量", default=0)
    valid_lead = models.IntegerField("有效线索", default=0)
    acquisition_cost = models.DecimalField("获客成本(元)", max_digits=10, decimal_places=2, default=0)
    account_setup = models.TextField("账户搭建", blank=True)
    product_content = models.TextField("产品内容", blank=True)
    # 直播专属字段
    exposure = models.IntegerField("直播曝光人数", default=0)
    enter_room = models.IntegerField("直播进房人数", default=0)
    avg_online = models.DecimalField("平均在线人数", max_digits=10, decimal_places=2, default=0)
    avg_stay = models.DecimalField("人均停留时长(分)", max_digits=8, decimal_places=2, default=0)
    live_duration = models.DecimalField("直播时长(分)", max_digits=10, decimal_places=2, default=0)
    live_cost = models.DecimalField("投流消耗(元)", max_digits=12, decimal_places=2, default=0)
    live_lead = models.IntegerField("留资数", default=0)
    live_valid_lead = models.IntegerField("有效留资数", default=0)
    lead_cost = models.DecimalField("留资成本(元)", max_digits=10, decimal_places=2, default=0)
    remark = models.TextField("备注", blank=True)

    class Meta:
        verbose_name = "主播获客日报"
        verbose_name_plural = verbose_name
        ordering = ["-date", "channel_type"]
        unique_together = ("channel_type", "date", "operator", "anchor_name")

    def __str__(self):
        return f"{self.get_channel_type_display()}-{self.date}"

    @property
    def enter_rate(self):
        """进房率 = 进房人数 / 曝光人数"""
        if self.exposure:
            return round(self.enter_room / self.exposure * 100, 2)
        return 0


class LeadLedger(BaseModel):
    """客户留资明细台账（支持增删改查，录入后自动汇总到每日报表总留资）"""
    CHANNEL = [
        ("PAID", "渠道获客-付费投放"),
        ("LIVE", "直播获客"),
        ("LOCAL_PUSH", "本地推投流获客"),
        ("AI", "AI获客"),
        ("SOCIAL", "视频号/小红书/闲鱼获客"),
        ("OTHER", "其他"),
    ]
    channel = models.CharField("渠道", max_length=20, choices=CHANNEL, default="LIVE", db_index=True)
    date = models.DateField("日期", db_index=True)
    customer_name = models.CharField("客户姓名", max_length=100)
    contact = models.CharField("客户联系方式", max_length=100, blank=True)
    need = models.TextField("客户需求", blank=True)
    address = models.TextField("客户地址", blank=True)
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="led_follow_leads", verbose_name="跟进人员")
    is_passed = models.BooleanField("客户是否通过", default=False)
    detail = models.TextField("客户详情备注", blank=True)
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="lead_ledgers", verbose_name="录入人")

    class Meta:
        verbose_name = "客户留资明细"
        verbose_name_plural = verbose_name
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.customer_name}-{self.date}"


class AnchorAdStat(BaseModel):
    """直播投流数据：短视频图文投流 / 直播间投流 两套分开统计"""
    AD_TYPE = [
        ("SHORT_VIDEO", "短视频图文投流"),
        ("LIVE_ROOM", "直播间投流"),
    ]
    ad_type = models.CharField("投流类型", max_length=20, choices=AD_TYPE, default="SHORT_VIDEO", db_index=True)
    date = models.DateField("日期", db_index=True)
    platform = models.CharField("投放平台", max_length=50, blank=True)
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="anchor_ad_stats", verbose_name="录入人")
    cost = models.DecimalField("消耗金额(元)", max_digits=12, decimal_places=2, default=0)
    impression = models.IntegerField("展示次数", default=0)
    click = models.IntegerField("点击次数", default=0)
    private_msg = models.IntegerField("私信咨询数", default=0)
    lead_count = models.IntegerField("线索留资数", default=0)
    remark = models.TextField("备注", blank=True)

    class Meta:
        verbose_name = "直播投流数据"
        verbose_name_plural = verbose_name
        ordering = ["-date", "ad_type"]

    def __str__(self):
        return f"{self.get_ad_type_display()}-{self.date}"

    @property
    def lead_cost(self):
        """留资成本 = 消耗 / 线索留资数"""
        if self.lead_count:
            return round(float(self.cost) / self.lead_count, 2)
        return 0

    @property
    def click_rate(self):
        if self.impression:
            return round(self.click / self.impression * 100, 2)
        return 0


class CostRecord(BaseModel):
    """运营成本记录（2026-11-02 Boss 指示：数据录入新增「成本录入」功能）

    与每日投放数据（AdDailyStat.cost=当日花费）互补：
    记录充值、推广、人工、工具等公司经营成本，管理层/老板看全量，员工仅看自己录入的。
    """
    CATEGORY = [
        ("RECHARGE", "账户充值"), ("PROMO", "推广费"), ("SALARY", "人工成本"),
        ("TOOL", "工具费用"), ("MATERIAL", "物料制作"), ("OTHER", "其他"),
    ]

    date = models.DateField("成本日期", db_index=True)
    category = models.CharField("成本类别", max_length=20, choices=CATEGORY, default="RECHARGE")
    platform = models.ForeignKey(AdPlatform, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="cost_records", verbose_name="所属平台")
    name = models.CharField("成本事项", max_length=200, blank=True)
    amount = models.DecimalField("金额(元)", max_digits=12, decimal_places=2, default=0)
    remark = models.CharField("备注", max_length=300, blank=True)

    class Meta:
        db_table = "ops_cost_record"
        verbose_name = "运营成本记录"
        verbose_name_plural = "运营成本记录"
        ordering = ["-date", "-created_at"]

    def category_label(self):
        return self.get_category_display()

    def __str__(self):
        return f"{self.date}-{self.get_category_display()}-{self.amount}"
