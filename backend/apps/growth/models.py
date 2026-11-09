"""增长中心（growth）· 纯增量模块

覆盖需求：
  1. 多平台线索录入（抖音/小红书/百度/高德/美团/闲鱼 + 预留京东/淘宝/拼多多）
  2. 线索全链路流转 + 三级权限隔离 + 公共线索池（公海）
  3. 3570 客户成交阶段标签（人工标记）
  4. 会计部下「外勤」子模块：任务接收 + 进度上报 + 销售端可视
  5. 独立「增值业务部」台账

【铁律】本 app 不修改任何既有模型与逻辑，仅通过外键引用：
  - accounts.User（用户）
  - sales.Lead（原线索，一对一扩展，不新增字段到 Lead 本身）
所有模型继承 apps.common.models.BaseModel（含 created_by / 软删除 / 时间戳）。
"""
from django.db import models
from django.conf import settings
from apps.common.models import BaseModel

User = settings.AUTH_USER_MODEL


# ----------------------------------------------------------------------------
# 一、投放渠道 / 平台字典
# ----------------------------------------------------------------------------
class LeadChannel(BaseModel):
    """投放渠道平台字典（后台可开关，含预留扩展位）

    与旧 ops.AdPlatform / sales.Lead.SOURCE 完全解耦，不修改它们。
    预留平台 is_reserved=True 时前端默认隐藏，后台一键开启即可启用。
    """
    code = models.CharField("平台编码", max_length=30, unique=True, db_index=True)
    name = models.CharField("平台名称", max_length=50)
    is_enabled = models.BooleanField("已启用", default=True)
    is_reserved = models.BooleanField(
        "预留扩展位", default=False,
        help_text="预留平台（后续可直接开启）：京东 / 淘宝 / 拼多多")
    sort = models.IntegerField("排序", default=0)

    class Meta:
        verbose_name = "投放渠道"
        verbose_name_plural = "投放渠道"
        ordering = ["sort", "id"]

    def __str__(self):
        return self.name


# ----------------------------------------------------------------------------
# 二、线索扩展信息（一对一挂到 sales.Lead，不改动 Lead 本身）
# ----------------------------------------------------------------------------
class LeadExt(BaseModel):
    """线索扩展信息

    承载本次新增的 4 个必填项：
      - 线索来源平台      → channel
      - 来源账号编号      → source_account_no（多账号区分）
      - 客户联系方式      → contact_type / contact_value（微信 / 电话）
      - 归属运营人        → ops_owner
    以及流转承接人 closer、3570 阶段标签、公海标记。
    """
    CONTACT_TYPE = [("WECHAT", "微信"), ("PHONE", "电话")]
    STAGE_3570 = [
        ("S3", "3阶段"),
        ("S5", "5阶段"),
        ("S7", "7阶段"),
        ("S0", "0成交"),
        # 2026-11-09 Boss 指示：有的客户既不属于 3/5/7/0（没有需求），增加「无需求」阶段
        ("SN", "无需求"),
    ]

    lead = models.OneToOneField(
        "sales.Lead", on_delete=models.CASCADE, related_name="growth_ext",
        verbose_name="关联线索")
    channel = models.ForeignKey(
        LeadChannel, on_delete=models.PROTECT, related_name="leads",
        verbose_name="线索来源平台")
    source_account_no = models.CharField(
        "来源账号编号", max_length=100, db_index=True,
        help_text="多账号区分，如抖音矩阵下的具体投放账号编号")
    contact_type = models.CharField(
        "客户联系方式", max_length=10, choices=CONTACT_TYPE, default="PHONE")
    contact_value = models.CharField("联系方式内容", max_length=100, blank=True)

    ops_owner = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="growth_input_leads", verbose_name="归属运营人")
    closer = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="growth_closing_leads", verbose_name="成交师/承接人")

    stage_3570 = models.CharField(
        "3570阶段", max_length=5, choices=STAGE_3570, blank=True, default="",
        help_text="人工手动标记，不强制自动算法；S0=0成交阶段")
    in_pool = models.BooleanField("在公海池", default=False, db_index=True)
    # ---- 2026-09-12 增量：线索录入中心新字段 ----
    customer_need = models.TextField("客户需求", blank=True, default="")
    contact_person = models.CharField("对接人", max_length=50, blank=True, default="")
    acquisition_cost = models.DecimalField(
        "获客成本(元)", max_digits=12, decimal_places=2, default=0,
        help_text="由业务人员手动填写，用于投产比统计")
    deal_amount = models.DecimalField(
        "签单金额(元)", max_digits=14, decimal_places=2, default=0,
        help_text="录入成交金额，系统据此自动计算转化率与占比")
    extra = models.JSONField("扩展字段", default=dict, blank=True)

    class Meta:
        verbose_name = "线索扩展信息"
        verbose_name_plural = "线索扩展信息"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Ext#{self.lead_id}-{self.channel}"

    @property
    def is_deal(self):
        """是否已成交（用于转化率统计）：签单金额>0 或 原线索状态为已成交"""
        return (self.deal_amount or 0) > 0 or (self.lead and self.lead.status == "DEAL")

    @property
    def conversion_rate(self):
        """该线索转化率取值（单条无意义，用于看板聚合时统一口径）：成交=1，否则=0"""
        return 1 if self.is_deal else 0


class LeadFlow(BaseModel):
    """线索流转记录（每一次流转都留痕）

    闭环：运营录入 → 自动流转成交师 → 成交师承接 → （无法跟进）退回公海 → 二次领取
    """
    ACTION = [
        ("SUBMIT", "运营录入"),
        ("AUTO_ASSIGN", "自动流转"),
        ("ACCEPT", "成交师承接"),
        ("RETURN_POOL", "退回公海"),
        ("CLAIM", "公海领取"),
        ("TRANSFER", "转派他人"),
        ("ASSIGN", "管理员分配"),
        ("DEAL", "成交"),
        ("INVALID", "标记无效"),
    ]
    lead_ext = models.ForeignKey(
        LeadExt, on_delete=models.CASCADE, related_name="flows", verbose_name="线索")
    action = models.CharField("动作", max_length=20, choices=ACTION)
    from_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="growth_flows_out", verbose_name="来源人")
    to_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="growth_flows_in", verbose_name="接收人")
    remark = models.TextField("备注", blank=True)

    class Meta:
        verbose_name = "线索流转记录"
        verbose_name_plural = "线索流转记录"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.lead_ext_id}-{self.get_action_display()}"


class LeadStageLog(BaseModel):
    """3570 阶段变更留痕（人工手动标记的历史）"""
    lead_ext = models.ForeignKey(
        LeadExt, on_delete=models.CASCADE, related_name="stage_logs", verbose_name="线索")
    old_stage = models.CharField("原阶段", max_length=5, blank=True, default="")
    # 2026-11-09：取消标记（清空阶段）也要留痕，new_stage 允许为空
    new_stage = models.CharField("新阶段", max_length=5, choices=LeadExt.STAGE_3570,
                                 blank=True, default="")
    remark = models.CharField("备注", max_length=300, blank=True)

    class Meta:
        verbose_name = "3570阶段变更记录"
        verbose_name_plural = "3570阶段变更记录"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.lead_ext_id}:{self.old_stage}→{self.new_stage}"


# ----------------------------------------------------------------------------
# 三、公共线索池（公海）
# ----------------------------------------------------------------------------
class LeadPool(BaseModel):
    """公共线索池（公海）

    承接人无法跟进 → 退回公海 → 支持二次分配/被他人领取。
    """
    # 2026-11-03 Boss 指示：文案细化「待承接 / 已承接」
    STATUS = [("WAITING", "待承接"), ("CLAIMED", "已承接")]
    lead_ext = models.OneToOneField(
        LeadExt, on_delete=models.CASCADE, related_name="pool", verbose_name="线索")
    status = models.CharField("状态", max_length=10, choices=STATUS, default="WAITING")
    returned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="growth_pool_returned", verbose_name="退回人")
    returned_reason = models.CharField("退回原因", max_length=300, blank=True)
    returned_at = models.DateTimeField("退回时间", null=True, blank=True)
    claimed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="growth_pool_claimed", verbose_name="领取人")
    claimed_at = models.DateTimeField("领取时间", null=True, blank=True)
    claim_count = models.IntegerField("被领取次数", default=0)

    class Meta:
        verbose_name = "公共线索池"
        verbose_name_plural = "公共线索池"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Pool#{self.lead_ext_id}-{self.get_status_display()}"


# ----------------------------------------------------------------------------
# 四、会计部下「外勤」子模块
# ----------------------------------------------------------------------------
class FieldTask(BaseModel):
    # 自动编号：派单号
    AUTO_NO_FIELDS = {"task_no": "WD"}
    """外勤任务（销售下单 → 外勤人员接收办理）"""
    STATUS = [
        ("PENDING", "待接收"),
        ("ACCEPTED", "已接收"),
        ("IN_PROGRESS", "办理中"),
        ("DONE", "已完成"),
        ("CLOSED", "已关闭"),
    ]
    BUSINESS_TYPE = [
        ("REGISTER", "工商注册"),
        ("CANCEL", "公司注销"),
        ("CHANGE", "工商变更"),
        ("ADDRESS_ABNORMAL", "地址异常"),
        ("TAX_REGISTER", "税务报到"),
        ("ABNORMAL", "异常处理"),
        ("GENERAL", "通用"),
    ]
    title = models.CharField("任务标题", max_length=200)
    order_no = models.CharField("关联单号", max_length=60, blank=True, db_index=True)
    customer_name = models.CharField("客户名称", max_length=200, blank=True)
    CUSTOMER_TYPE = [
        ("ENTERPRISE", "企业"), ("INDIVIDUAL", "个体工商户"), ("PERSONAL", "个人"),
    ]
    customer_type = models.CharField(
        "客户类型", max_length=20, choices=CUSTOMER_TYPE, default="ENTERPRISE")
    # 业务流转：电销/运营成交订单自动流转到外勤任务池时的来源单号
    from_order_no = models.CharField("来源成交单号", max_length=60, blank=True, db_index=True)
    # 派单号（外勤任务系统编号，自动生成）
    task_no = models.CharField("派单号", max_length=32, blank=True, db_index=True,
                                help_text="外勤派单系统编号，由系统自动生成")
    from_deal_id = models.IntegerField("来源成交记录ID", null=True, blank=True)
    business_type = models.CharField(
        "业务类型", max_length=20, choices=BUSINESS_TYPE, default="GENERAL")
    task_type = models.CharField(
        "任务类型", max_length=60, blank=True,
        help_text="如：工商注册、异常处理、注销、税务报到、地址异常")
    address = models.CharField("办理地点", max_length=300, blank=True)
    assignee = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="field_tasks", verbose_name="外勤人员")
    # 主管手动录入的外勤人员姓名（当指派给系统外/未注册人员时，作为自由文本留存）
    assignee_name = models.CharField(
        "外勤人员名称", max_length=100, blank=True, null=True,
        help_text="主管手动录入的外勤人员姓名；优先使用系统用户，无匹配时作为自由文本保存")
    # 派单人（外勤主管将任务派给外勤时记录），用于主管可编辑其分配出去的任务
    assigned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_field_tasks", verbose_name="派单人")
    creator = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_field_tasks", verbose_name="下单销售")
    status = models.CharField("状态", max_length=20, choices=STATUS, default="PENDING")
    due_at = models.DateTimeField("要求完成时间", null=True, blank=True)
    accepted_at = models.DateTimeField("接收时间", null=True, blank=True)
    finished_at = models.DateTimeField("完成时间", null=True, blank=True)
    remark = models.TextField("备注", blank=True)

    # 按业务类型预置的节点模板：外勤接单后按此模板自动生成进度节点
    NODE_TEMPLATES = {
        "REGISTER":       ["DOC_CONFIRM", "NAME_VERIFY", "LICENSE", "SEAL", "BANK", "TAX", "SOCIAL"],
        "CANCEL":         ["DOC_CONFIRM", "TAX_CLEAR", "LICENSE_CANCEL", "BANK_CLOSE", "SOCIAL_REDUCE"],
        "CHANGE":         ["DOC_CONFIRM", "LICENSE_CHANGE", "LICENSE_REISSUE", "TAX_CHANGE", "BANK_CHANGE"],
        "ADDRESS_ABNORMAL": ["DOC_CONFIRM", "ADDRESS_FIX", "LICENSE_UPDATE", "TAX_SYNC"],
        "TAX_REGISTER":   ["DOC_CONFIRM", "TAX_TYPE", "INVOICE_APPLY", "FIRST_DECLARE"],
        "ABNORMAL":       ["DOC_CONFIRM", "DIAGNOSE", "PAYMENT", "ABNORMAL_CLEAR"],
        "GENERAL":        ["DOC_CONFIRM", "HANDLE", "DELIVER"],
    }

    class Meta:
        verbose_name = "外勤任务"
        verbose_name_plural = "外勤任务"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title}-{self.get_status_display()}"


class FieldProgress(BaseModel):
    """外勤进度上报（每单可实时更新办理节点，销售端可自主查看）"""
    task = models.ForeignKey(
        FieldTask, on_delete=models.CASCADE, related_name="progresses", verbose_name="外勤任务")
    node = models.CharField("办理节点", max_length=100, help_text="如：已取件 / 已提交 / 待审核 / 已办结")
    content = models.TextField("进度说明", blank=True)
    reported_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="field_progresses", verbose_name="上报人")

    class Meta:
        verbose_name = "外勤进度上报"
        verbose_name_plural = "外勤进度上报"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.task_id}-{self.node}"


# ----------------------------------------------------------------------------
# 五、增值业务部（独立台账）
# ----------------------------------------------------------------------------
class ValueAddedProject(BaseModel):
    """增值业务部项目台账（独立菜单 / 独立数据台账）"""
    STATUS = [
        ("DRAFT", "待启动"),
        ("DOING", "进行中"),
        ("DONE", "已完成"),
        ("PAUSED", "已暂停"),
        ("CANCELED", "已取消"),
    ]
    name = models.CharField("项目名称", max_length=200)
    customer_name = models.CharField("客户名称", max_length=200, blank=True)
    project_type = models.CharField(
        "业务类型", max_length=60, blank=True,
        help_text="如：高新认定、资质办理、税务筹划、审计、验资")
    owner = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="va_projects", verbose_name="负责人")
    amount = models.DecimalField("合同金额", max_digits=12, decimal_places=2, default=0)
    cost = models.DecimalField("成本", max_digits=12, decimal_places=2, default=0)
    status = models.CharField("状态", max_length=20, choices=STATUS, default="DRAFT")
    started_at = models.DateField("启动日期", null=True, blank=True)
    finished_at = models.DateField("完成日期", null=True, blank=True)
    # ---- 2026-09-12 增量：增值业务开启合同上传，适配续费 / 客户上门拜访 ----
    is_renewal = models.BooleanField("续费业务", default=False, help_text="标记该单为续费场景")
    is_visit = models.BooleanField("客户上门拜访", default=False, help_text="标记该单涉及客户上门拜访")
    contract_attachment = models.FileField(
        "合同附件(PDF/扫描件)", upload_to="va_contracts/", null=True, blank=True,
        help_text="本地上传 PDF 电子合同 / 合同扫描件；预留后期对接第三方电子签章跳转")
    remark = models.TextField("备注", blank=True)

    class Meta:
        verbose_name = "增值业务项目"
        verbose_name_plural = "增值业务项目"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def profit(self):
        return (self.amount or 0) - (self.cost or 0)


# ----------------------------------------------------------------------------
# 七、增长中心独立角色（不改动 accounts.User.ROLE_CHOICES）
# ----------------------------------------------------------------------------
class GrowthRole(BaseModel):
    """增长中心独立角色分配

    旧 User.ROLE_CHOICES 是硬编码的组织角色（BOSS/MANAGER/LEADER/EMPLOYEE/HR），
    无法表达「成交师 / 外勤 / 增值业务专员」等职能角色，且铁律要求零改动旧模型。
    故以独立角色表扩展：一个用户在增长中心拥有一个职能角色。
    """
    ROLE = [
        ("OPS", "运营"),
        ("CLOSER", "成交师"),
        ("FIELD", "外勤"),
        ("VA_STAFF", "增值业务专员"),
        ("VA_MANAGER", "增值业务主管"),
        ("OBSERVER", "观察者"),
    ]
    DEPT = [
        ("OPS", "运营部"),
        ("VALUE_ADDED", "增值业务部"),
        ("FIELD_WORK", "外勤组（会计部下）"),
    ]
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="growth_role", verbose_name="用户")
    role = models.CharField("职能角色", max_length=20, choices=ROLE, default="OBSERVER")
    dept_key = models.CharField("归属新部门", max_length=20, choices=DEPT, blank=True, default="")
    can_view_all = models.BooleanField(
        "可查看全公司数据", default=False,
        help_text="超级总账号开启：可查看所有线索、所有对接人、所有进度")

    class Meta:
        verbose_name = "增长中心角色"
        verbose_name_plural = "增长中心角色"
        ordering = ["id"]

    def __str__(self):
        return f"{self.user}-{self.get_role_display()}"


# ----------------------------------------------------------------------------
# 六、成交师 × 平台 专项分配绑定（按平台专项派单）
# ----------------------------------------------------------------------------
class CloserChannel(BaseModel):
    """成交师负责的平台（专项分配）

    派单优先级：
      1. 该平台有专项绑定的成交师 → 在其中按在手负载最少分配
      2. 无专项绑定 → 降级到全平台成交师按负载分配
      3. 仍无可用成交师 → 自动进入公海
    """
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="closer_channels", verbose_name="成交师")
    channel = models.ForeignKey(
        LeadChannel, on_delete=models.CASCADE, related_name="closers", verbose_name="负责平台")
    priority = models.IntegerField(
        "优先级", default=0, help_text="数字越大越优先，同平台多人时按此排序")
    is_active = models.BooleanField("启用", default=True)

    class Meta:
        verbose_name = "成交师平台专项"
        verbose_name_plural = "成交师平台专项"
        ordering = ["-priority", "id"]
        unique_together = [("user", "channel")]

    def __str__(self):
        return f"{self.user}-{self.channel}"


# ----------------------------------------------------------------------------
# 七、投放消耗（按平台/日期录入，用于投产比统计）
# ----------------------------------------------------------------------------
class AdSpendRecord(BaseModel):
    """投放消耗记录（按平台 + 日期 + 账号录入）

    独立于旧 ops.AdDailyStat，不改动旧投放模块，仅为本面板统计服务。
    """
    channel = models.ForeignKey(
        LeadChannel, on_delete=models.CASCADE, related_name="spends", verbose_name="投放平台")
    account_no = models.CharField("投放账号编号", max_length=100, blank=True, db_index=True)
    stat_date = models.DateField("统计日期", db_index=True)
    cost = models.DecimalField("消耗金额", max_digits=12, decimal_places=2, default=0)
    impressions = models.IntegerField("曝光数", default=0)
    clicks = models.IntegerField("点击数", default=0)
    owner = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ad_spends", verbose_name="投放运营")
    remark = models.CharField("备注", max_length=300, blank=True)

    class Meta:
        verbose_name = "投放消耗记录"
        verbose_name_plural = "投放消耗记录"
        ordering = ["-stat_date", "-id"]
        unique_together = [("channel", "account_no", "stat_date")]

    def __str__(self):
        return f"{self.channel}-{self.stat_date}-{self.cost}"


# ----------------------------------------------------------------------------
# 六（续）、线索跟进记录（支持多次添加：第一次 / 二次 / 三次跟进）
# ----------------------------------------------------------------------------
class LeadFollowUp(BaseModel):
    """线索跟进记录（与 LeadExt 一对一关联，可录入多条，最多三次跟进）"""
    ROUND = [
        (1, "第一次跟进"),
        (2, "第二次跟进"),
        (3, "第三次跟进"),
    ]
    WAY = [("PHONE", "电话"), ("WECHAT", "微信"), ("VISIT", "上门"), ("MEETING", "会议"), ("OTHER", "其他")]
    lead_ext = models.ForeignKey(
        LeadExt, on_delete=models.CASCADE, related_name="followups", verbose_name="线索")
    round_no = models.IntegerField("跟进轮次", choices=ROUND, default=1)
    way = models.CharField("跟进方式", max_length=20, choices=WAY, default="PHONE")
    content = models.TextField("跟进内容")
    follow_at = models.DateTimeField("跟进时间", null=True, blank=True)
    # 该次跟进是否产生成交（用于转化率统计）
    deal_happened = models.BooleanField("本次成交", default=False)
    deal_amount = models.DecimalField(
        "本次签单金额", max_digits=14, decimal_places=2, default=0)

    class Meta:
        verbose_name = "线索跟进记录"
        verbose_name_plural = "线索跟进记录"
        ordering = ["round_no", "created_at"]

    def __str__(self):
        return f"FUP#{self.lead_ext_id}-R{self.round_no}"


# ----------------------------------------------------------------------------
# 七（续）、外勤精细化任务进度节点
#   固定节点：资料确认 / 办理执照 / 刻章 / 银行开户 / 税务登记
#   每个节点可填写完成日期；状态：待处理 / 进行中 / 已完成（颜色标记）
# ----------------------------------------------------------------------------
class FieldTaskNode(BaseModel):
    """外勤任务进度节点（按业务类型预置模板，支持点选）"""
    NODES = [
        # 通用
        ("DOC_CONFIRM", "资料确认"),
        ("HANDLE", "业务办理"),
        ("DELIVER", "结果交付"),
        # 注册类
        ("NAME_VERIFY", "工商核名"),
        ("LICENSE", "办理执照"),
        ("SEAL", "刻章"),
        ("BANK", "银行开户"),
        ("TAX", "税务登记"),
        ("SOCIAL", "社保开户"),
        # 注销类
        ("TAX_CLEAR", "税务清税"),
        ("LICENSE_CANCEL", "工商注销"),
        ("BANK_CLOSE", "银行销户"),
        ("SOCIAL_REDUCE", "社保/公积金减员"),
        # 变更类
        ("LICENSE_CHANGE", "工商变更"),
        ("LICENSE_REISSUE", "换发执照"),
        ("TAX_CHANGE", "税务变更"),
        ("BANK_CHANGE", "银行信息变更"),
        # 地址异常类
        ("ADDRESS_FIX", "解除地址异常"),
        ("LICENSE_UPDATE", "工商更新"),
        ("TAX_SYNC", "税务同步"),
        # 税务报到类
        ("TAX_TYPE", "税种核定"),
        ("INVOICE_APPLY", "发票申领"),
        ("FIRST_DECLARE", "首次申报"),
        # 异常处理类
        ("DIAGNOSE", "异常诊断"),
        ("PAYMENT", "补缴/罚款"),
        ("ABNORMAL_CLEAR", "解除异常"),
    ]
    STATUS = [
        ("PENDING", "待处理"),
        ("IN_PROGRESS", "进行中"),
        ("DONE", "已完成"),
    ]
    task = models.ForeignKey(
        FieldTask, on_delete=models.CASCADE, related_name="nodes", verbose_name="外勤任务")
    node = models.CharField("节点", max_length=20, choices=NODES, default="DOC_CONFIRM")
    status = models.CharField("状态", max_length=20, choices=STATUS, default="PENDING")
    done_at = models.DateField("完成日期", null=True, blank=True)
    remark = models.CharField("说明", max_length=300, blank=True)
    order = models.IntegerField("排序", default=0)

    class Meta:
        verbose_name = "外勤进度节点"
        verbose_name_plural = "外勤进度节点"
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.task_id}-{self.get_node_display()}"
