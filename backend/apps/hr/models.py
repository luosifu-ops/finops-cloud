"""人事考勤与审批"""
from django.db import models
from django.conf import settings
from apps.common.models import BaseModel
from apps.accounts.models import Department, Position, User


class AttendanceRule(BaseModel):
    """考勤规则"""
    name = models.CharField("规则名称", max_length=50, default="默认考勤")
    work_start = models.TimeField("上班时间", default="09:00")
    work_end = models.TimeField("下班时间", default="18:00")
    late_minutes = models.IntegerField("迟到宽限(分钟)", default=10)
    late_penalty = models.DecimalField("迟到罚款(元/次)", max_digits=8, decimal_places=2, default=0)
    absent_penalty = models.DecimalField("旷工罚款(元/天)", max_digits=8, decimal_places=2, default=0)
    work_days = models.CharField("工作日", max_length=50, default="1,2,3,4,5")
    is_default = models.BooleanField("默认规则", default=False)

    class Meta:
        verbose_name = "考勤规则"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Attendance(models.Model):
    """考勤记录"""
    STATUS = [
        ("NORMAL", "正常"), ("LATE", "迟到"), ("EARLY", "早退"),
        ("ABSENT", "旷工"), ("LEAVE", "请假"), ("TRIP", "出差"),
        ("OVERTIME", "加班"), ("REST", "休息"), ("FIELD", "外勤"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="attendances", verbose_name="员工")
    date = models.DateField("日期", db_index=True)
    check_in = models.DateTimeField("上班打卡", null=True, blank=True)
    check_out = models.DateTimeField("下班打卡", null=True, blank=True)
    check_in_location = models.CharField("打卡地点", max_length=200, blank=True)
    check_out_location = models.CharField("签退地点", max_length=200, blank=True)
    status = models.CharField("状态", max_length=20, choices=STATUS, default="NORMAL")
    late_minutes = models.IntegerField("迟到分钟", default=0)
    work_hours = models.DecimalField("工作时长(小时)", max_digits=5, decimal_places=2, default=0)
    remark = models.CharField("备注", max_length=300, blank=True)

    class Meta:
        verbose_name = "考勤记录"
        verbose_name_plural = verbose_name
        unique_together = ("user", "date")
        ordering = ["-date", "user"]

    def __str__(self):
        return f"{self.user}-{self.date}-{self.get_status_display()}"


class AttendanceStat(models.Model):
    """月度考勤汇总"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="attendance_stats", verbose_name="员工")
    month = models.CharField("月份", max_length=7, db_index=True)  # 2026-09
    normal_days = models.DecimalField("正常出勤", max_digits=5, decimal_places=1, default=0)
    late_times = models.IntegerField("迟到次数", default=0)
    early_times = models.IntegerField("早退次数", default=0)
    absent_days = models.DecimalField("旷工天数", max_digits=5, decimal_places=1, default=0)
    leave_days = models.DecimalField("请假天数", max_digits=5, decimal_places=1, default=0)
    overtime_hours = models.DecimalField("加班时长", max_digits=6, decimal_places=1, default=0)
    penalty = models.DecimalField("扣款合计", max_digits=10, decimal_places=2, default=0)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "考勤月报"
        verbose_name_plural = verbose_name
        unique_together = ("user", "month")
        ordering = ["-month"]


class LeaveApplication(BaseModel):
    """请假申请"""
    LEAVE_TYPE = [
        ("PERSONAL", "事假"), ("SICK", "病假"), ("ANNUAL", "年假"),
        ("OFF", "调休"), ("MARRIAGE", "婚假"), ("MATERNITY", "产假"),
        ("FUNERAL", "丧假"), ("OTHER", "其他"),
    ]
    STATUS = [("DRAFT", "草稿"), ("PENDING", "审批中"), ("APPROVED", "已通过"),
              ("REJECTED", "已驳回"), ("CANCELED", "已取消")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="leaves", verbose_name="申请人")
    leave_type = models.CharField("请假类型", max_length=20, choices=LEAVE_TYPE, default="PERSONAL")
    start_at = models.DateTimeField("开始时间")
    end_at = models.DateTimeField("结束时间")
    days = models.DecimalField("请假天数", max_digits=5, decimal_places=1, default=0)
    reason = models.TextField("请假事由", blank=True)
    attachment = models.FileField("附件(病假条等)", upload_to="leave/", null=True, blank=True)
    status = models.CharField("审批状态", max_length=20, choices=STATUS, default="PENDING")
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="approved_leaves", verbose_name="审批人")
    approved_at = models.DateTimeField("审批时间", null=True, blank=True)
    approve_remark = models.TextField("审批意见", blank=True)

    class Meta:
        verbose_name = "请假申请"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user}-{self.get_leave_type_display()}-{self.days}天"


class OvertimeApplication(BaseModel):
    """加班申请"""
    STATUS = [("PENDING", "审批中"), ("APPROVED", "已通过"), ("REJECTED", "已驳回")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="overtimes", verbose_name="申请人")
    start_at = models.DateTimeField("开始时间")
    end_at = models.DateTimeField("结束时间")
    hours = models.DecimalField("加班时长", max_digits=5, decimal_places=1, default=0)
    reason = models.TextField("加班事由", blank=True)
    compensate = models.CharField("补偿方式", max_length=20,
                                  choices=[("MONEY", "加班费"), ("OFF", "调休")], default="OFF")
    status = models.CharField("审批状态", max_length=20, choices=STATUS, default="PENDING")
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="approved_overtimes", verbose_name="审批人")
    approved_at = models.DateTimeField("审批时间", null=True, blank=True)

    class Meta:
        verbose_name = "加班申请"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]


class TravelApplication(BaseModel):
    """出差申请"""
    STATUS = [("PENDING", "审批中"), ("APPROVED", "已通过"), ("REJECTED", "已驳回")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="travels", verbose_name="申请人")
    destination = models.CharField("出差地点", max_length=100)
    start_at = models.DateTimeField("开始时间")
    end_at = models.DateTimeField("结束时间")
    days = models.DecimalField("天数", max_digits=5, decimal_places=1, default=0)
    reason = models.TextField("出差事由", blank=True)
    budget = models.DecimalField("预计费用", max_digits=10, decimal_places=2, default=0)
    status = models.CharField("审批状态", max_length=20, choices=STATUS, default="PENDING")
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="approved_travels", verbose_name="审批人")
    approved_at = models.DateTimeField("审批时间", null=True, blank=True)

    class Meta:
        verbose_name = "出差申请"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]


class ExpenseApplication(BaseModel):
    """报销申请"""
    CATEGORY = [("TRAVEL", "差旅费"), ("MEAL", "餐饮费"), ("OFFICE", "办公用品"),
                ("CLIENT", "客户招待"), ("AD", "推广费"), ("OTHER", "其他")]
    STATUS = [("PENDING", "审批中"), ("APPROVED", "已通过"), ("REJECTED", "已驳回"), ("PAID", "已支付")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="expenses", verbose_name="申请人")
    category = models.CharField("费用类型", max_length=20, choices=CATEGORY, default="OTHER")
    amount = models.DecimalField("报销金额", max_digits=10, decimal_places=2, default=0)
    happened_at = models.DateField("发生日期", null=True, blank=True)
    reason = models.TextField("事由", blank=True)
    invoice_no = models.CharField("发票号码", max_length=60, blank=True)
    attachment = models.FileField("票据照片", upload_to="expense/", null=True, blank=True)
    status = models.CharField("审批状态", max_length=20, choices=STATUS, default="PENDING")
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="approved_expenses", verbose_name="审批人")
    approved_at = models.DateTimeField("审批时间", null=True, blank=True)
    paid_at = models.DateTimeField("支付时间", null=True, blank=True)

    class Meta:
        verbose_name = "报销申请"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]


class Approval(BaseModel):
    """通用审批流引擎"""
    BIZ_TYPE = [
        ("LEAVE", "请假"), ("OVERTIME", "加班"), ("TRAVEL", "出差"),
        ("EXPENSE", "报销"), ("REGULAR", "转正"), ("RESIGN", "离职"),
        ("TRANSFER", "调岗"), ("RAISE", "调薪"), ("RENEW", "续签"),
        ("PURCHASE", "采购"), ("SEAL", "用印"), ("ENTRY", "入职"),
        ("CUSTOM", "自定义"),
    ]
    STATUS = [("PENDING", "审批中"), ("APPROVED", "已通过"), ("REJECTED", "已驳回"), ("CANCELED", "已撤销")]
    biz_type = models.CharField("业务类型", max_length=20, choices=BIZ_TYPE, default="CUSTOM")
    biz_id = models.IntegerField("业务ID", null=True, blank=True)
    title = models.CharField("审批标题", max_length=200)
    content = models.TextField("审批内容", blank=True)
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                  related_name="my_approvals", verbose_name="申请人")
    status = models.CharField("状态", max_length=20, choices=STATUS, default="PENDING")
    current_step = models.IntegerField("当前节点", default=1)
    finished_at = models.DateTimeField("完成时间", null=True, blank=True)

    class Meta:
        verbose_name = "审批单"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title}-{self.get_status_display()}"


class ApprovalStep(BaseModel):
    """审批节点"""
    STATUS = [("PENDING", "待审批"), ("APPROVED", "已同意"), ("REJECTED", "已驳回"), ("SKIPPED", "已跳过")]
    approval = models.ForeignKey(Approval, on_delete=models.CASCADE, related_name="steps", verbose_name="审批单")
    step = models.IntegerField("节点序号", default=1)
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                 related_name="approval_steps", verbose_name="审批人")
    status = models.CharField("状态", max_length=20, choices=STATUS, default="PENDING")
    remark = models.TextField("审批意见", blank=True)
    handled_at = models.DateTimeField("处理时间", null=True, blank=True)

    class Meta:
        verbose_name = "审批节点"
        verbose_name_plural = verbose_name
        ordering = ["step"]


# ============================================================================
# 钉钉智能人事 · 缺失功能补全（2026-09-12 增量）
# 原则：仅在系统缺失处嫁接新增，保留原有全部模块、组织架构、数据与接口。
# 权责归属：行政人事部；最高审批决策层：总经办。
# ============================================================================


class JobLevel(BaseModel):
    """岗位职级库（职级序列）"""
    SEQUENCE = [
        ("MANAGE", "管理序列"),
        ("SALES", "销售序列"),
        ("FINANCE", "财务会计序列"),
        ("OPS_HOST", "运营主播序列"),
        ("SUPPORT", "职能支持序列"),
    ]
    name = models.CharField("职级名称", max_length=50)
    sequence = models.CharField("职级序列", max_length=20, choices=SEQUENCE, default="SUPPORT")
    level = models.IntegerField("级别", default=1, help_text="1 最低，数字越大越高")
    description = models.TextField("职级说明", blank=True)

    class Meta:
        verbose_name = "岗位职级"
        verbose_name_plural = "岗位职级库"
        ordering = ["sequence", "level"]

    def __str__(self):
        return f"{self.get_sequence_display()}-{self.name}({self.level})"


class ExternalContact(BaseModel):
    """外部联系人（区别于内部员工通讯录）：客户 / 渠道合作方"""
    GROUP = [("CUSTOMER", "客户"), ("CHANNEL", "渠道合作方"), ("OTHER", "其他")]
    name = models.CharField("姓名", max_length=50)
    group = models.CharField("分组", max_length=20, choices=GROUP, default="CUSTOMER")
    company = models.CharField("单位/公司", max_length=100, blank=True)
    phone = models.CharField("联系电话", max_length=20, blank=True)
    wechat = models.CharField("微信", max_length=50, blank=True)
    position = models.CharField("职位", max_length=50, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name="external_contacts", verbose_name="负责人")
    remark = models.TextField("备注", blank=True)

    class Meta:
        verbose_name = "外部联系人"
        verbose_name_plural = "外部联系人"
        ordering = ["group", "name"]

    def __str__(self):
        return f"{self.get_group_display()}-{self.name}"


class UserAttachment(BaseModel):
    """员工证件 / 材料附件（身份证、学历、合同扫描等）"""
    CATEGORY = [
        ("ID_CARD", "身份证件"),
        ("EDUCATION", "学历证明"),
        ("CONTRACT", "劳动合同"),
        ("BANK", "银行卡"),
        ("PHOTO", "证件照"),
        ("OTHER", "其他"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="attachments", verbose_name="员工")
    category = models.CharField("材料类别", max_length=20, choices=CATEGORY, default="OTHER")
    file = models.FileField("附件", upload_to="user_docs/")
    remark = models.CharField("说明", max_length=200, blank=True)

    class Meta:
        verbose_name = "员工材料附件"
        verbose_name_plural = "员工材料附件"

    def __str__(self):
        return f"{self.user.display_name}-{self.get_category_display()}"


class EmployeeChangeLog(BaseModel):
    """员工资料变更记录（所有修改留痕）"""
    ACTION = [
        ("CREATE", "创建档案"), ("UPDATE", "资料变更"), ("TRANSFER", "调动"),
        ("REGULAR", "转正"), ("RESIGN", "离职"), ("CONTRACT", "合同变更"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="change_logs", verbose_name="员工")
    action = models.CharField("操作类型", max_length=20, choices=ACTION, default="UPDATE")
    field = models.CharField("变更字段", max_length=50, blank=True)
    old_value = models.TextField("原值", blank=True)
    new_value = models.TextField("新值", blank=True)
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                 related_name="made_changes", verbose_name="操作人")
    remark = models.TextField("说明", blank=True)

    class Meta:
        verbose_name = "员工变更日志"
        verbose_name_plural = "员工变更日志"
        ordering = ["-created_at"]


class LaborContract(BaseModel):
    # 自动编号：劳动合同编号
    AUTO_NO_FIELDS = {"contract_no": "LC"}
    """劳动合同台账（独立于销售合同）"""
    TYPE = [
        ("FULLTIME", "劳动合同"),
        ("INTERN", "实习协议"),
        ("PARTTIME", "劳务协议"),
    ]
    STATUS = [("ACTIVE", "生效中"), ("EXPIRED", "已到期"),
              ("TERMINATED", "已解除"), ("RENEWED", "已续签")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="labor_contracts", verbose_name="员工")
    contract_type = models.CharField("合同类型", max_length=20, choices=TYPE, default="FULLTIME")
    contract_no = models.CharField("合同编号", max_length=50, blank=True)
    start_date = models.DateField("合同起始", null=True, blank=True)
    end_date = models.DateField("合同终止", null=True, blank=True)
    signed_date = models.DateField("签订日期", null=True, blank=True)
    status = models.CharField("状态", max_length=20, choices=STATUS, default="ACTIVE")
    is_renewal = models.BooleanField("是否续签", default=False)
    renewal_of = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="renewals", verbose_name="续签自")
    attachment = models.FileField("合同附件", upload_to="labor_contract/", null=True, blank=True)
    remark = models.TextField("备注", blank=True)

    class Meta:
        verbose_name = "劳动合同"
        verbose_name_plural = "劳动合同台账"
        ordering = ["-signed_date", "-created_at"]


class RegularizationApplication(BaseModel):
    """转正申请"""
    STATUS = [("PENDING", "审批中"), ("APPROVED", "已通过"), ("REJECTED", "已驳回")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="regularizations", verbose_name="申请人")
    probation_end = models.DateField("试用期到期", null=True, blank=True)
    apply_date = models.DateField("申请转正日期", null=True, blank=True)
    summary = models.TextField("试用期工作总结", blank=True)
    status = models.CharField("审批状态", max_length=20, choices=STATUS, default="PENDING")
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="approved_regularizations", verbose_name="审批人")
    approved_at = models.DateTimeField("审批时间", null=True, blank=True)
    approve_remark = models.TextField("审批意见", blank=True)
    approval = models.ForeignKey(Approval, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="regularizations", verbose_name="关联审批单")

    class Meta:
        verbose_name = "转正申请"
        verbose_name_plural = "转正申请"
        ordering = ["-created_at"]


class TransferApplication(BaseModel):
    """异动调岗 / 调级（审批通过自动同步通讯录部门/岗位/职级）"""
    STATUS = [("PENDING", "审批中"), ("APPROVED", "已通过"), ("REJECTED", "已驳回")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="transfers", verbose_name="员工")
    from_department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name="transfers_from", verbose_name="原部门")
    to_department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name="transfers_to", verbose_name="调入部门")
    from_position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name="transfers_from_p", verbose_name="原岗位")
    to_position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="transfers_to_p", verbose_name="调入岗位")
    from_job_level = models.ForeignKey(JobLevel, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name="transfers_from_jl", verbose_name="原职级")
    to_job_level = models.ForeignKey(JobLevel, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name="transfers_to_jl", verbose_name="调入职级")
    reason = models.TextField("异动原因", blank=True)
    status = models.CharField("审批状态", max_length=20, choices=STATUS, default="PENDING")
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="approved_transfers", verbose_name="审批人")
    approved_at = models.DateTimeField("审批时间", null=True, blank=True)
    approve_remark = models.TextField("审批意见", blank=True)
    approval = models.ForeignKey(Approval, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="transfers", verbose_name="关联审批单")

    class Meta:
        verbose_name = "异动调岗"
        verbose_name_plural = "异动调岗"
        ordering = ["-created_at"]


class ResignApplication(BaseModel):
    """离职申请 + 工作交接 + 离职台账（审批通过自动调整通讯录状态为已离职）"""
    STATUS = [("PENDING", "审批中"), ("APPROVED", "已通过"), ("REJECTED", "已驳回")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="resignations", verbose_name="离职人")
    resign_date = models.DateField("预计离职日期", null=True, blank=True)
    reason_type = models.CharField("离职原因", max_length=50, blank=True)
    reason = models.TextField("离职说明", blank=True)
    handover_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="handover_received", verbose_name="工作交接人")
    handover_items = models.TextField("交接事项", blank=True)
    status = models.CharField("审批状态", max_length=20, choices=STATUS, default="PENDING")
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="approved_resignations", verbose_name="审批人")
    approved_at = models.DateTimeField("审批时间", null=True, blank=True)
    approve_remark = models.TextField("审批意见", blank=True)
    approval = models.ForeignKey(Approval, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="resignations", verbose_name="关联审批单")

    class Meta:
        verbose_name = "离职申请"
        verbose_name_plural = "离职申请"
        ordering = ["-created_at"]


class AttendanceGroup(BaseModel):
    """考勤组（按部门划分，适配销售 / 主播轮班倒班）"""
    name = models.CharField("考勤组名称", max_length=50)
    departments = models.ManyToManyField(Department, blank=True,
                                         related_name="attendance_groups", verbose_name="适用部门")
    rule = models.ForeignKey(AttendanceRule, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name="groups", verbose_name="考勤规则")
    description = models.TextField("说明", blank=True)

    class Meta:
        verbose_name = "考勤组"
        verbose_name_plural = "考勤组"

    def __str__(self):
        return self.name


class ShiftSchedule(BaseModel):
    """排班（适配销售 / 主播轮班倒班）"""
    SHIFT = [("MORNING", "早班"), ("AFTERNOON", "午班"),
             ("NIGHT", "晚班/夜班"), ("REST", "休息")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="shifts", verbose_name="员工")
    date = models.DateField("排班日期")
    shift = models.CharField("班次", max_length=20, choices=SHIFT, default="MORNING")
    note = models.CharField("备注", max_length=100, blank=True)

    class Meta:
        verbose_name = "排班"
        verbose_name_plural = "排班表"
        unique_together = ("user", "date")
        ordering = ["-date", "user"]


class LeaveBalance(BaseModel):
    """假期余额（自动核算：请假/调休后回写已用）"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="leave_balances", verbose_name="员工")
    year = models.IntegerField("年份")
    annual_total = models.DecimalField("年假总额(天)", max_digits=5, decimal_places=1, default=0)
    annual_used = models.DecimalField("年假已用(天)", max_digits=5, decimal_places=1, default=0)
    personal_total = models.DecimalField("事假额度(天)", max_digits=5, decimal_places=1, default=0)
    personal_used = models.DecimalField("事假已用(天)", max_digits=5, decimal_places=1, default=0)
    compensate_total = models.DecimalField("调休总额(天)", max_digits=5, decimal_places=1, default=0)
    compensate_used = models.DecimalField("调休已用(天)", max_digits=5, decimal_places=1, default=0)

    class Meta:
        verbose_name = "假期余额"
        verbose_name_plural = "假期余额"
        unique_together = ("user", "year")
        ordering = ["-year", "user"]


class PurchaseApplication(BaseModel):
    """采购申请"""
    STATUS = [("PENDING", "审批中"), ("APPROVED", "已通过"), ("REJECTED", "已驳回"), ("DONE", "已采购")]
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                  related_name="purchases", verbose_name="申请人")
    item_name = models.CharField("采购物品", max_length=100)
    spec = models.CharField("规格/型号", max_length=100, blank=True)
    quantity = models.IntegerField("数量", default=1)
    amount = models.DecimalField("预算金额", max_digits=10, decimal_places=2, default=0)
    purpose = models.TextField("用途说明", blank=True)
    supplier = models.CharField("建议供应商", max_length=100, blank=True)
    status = models.CharField("审批状态", max_length=20, choices=STATUS, default="PENDING")
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="approved_purchases", verbose_name="审批人")
    approved_at = models.DateTimeField("审批时间", null=True, blank=True)
    approval = models.ForeignKey(Approval, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="purchases", verbose_name="关联审批单")

    class Meta:
        verbose_name = "采购申请"
        verbose_name_plural = "采购申请"
        ordering = ["-created_at"]


class SealApplication(BaseModel):
    """用印申请"""
    TYPE = [("CONTRACT", "合同章"), ("FINANCE", "财务章"), ("LEGAL", "公章"), ("INVOICE", "发票章")]
    STATUS = [("PENDING", "审批中"), ("APPROVED", "已通过"), ("REJECTED", "已驳回"), ("USED", "已用印")]
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                  related_name="seal_applications", verbose_name="申请人")
    seal_type = models.CharField("用印类型", max_length=20, choices=TYPE, default="CONTRACT")
    doc_name = models.CharField("用印文件", max_length=100)
    reason = models.TextField("用印事由", blank=True)
    use_date = models.DateField("用印日期", null=True, blank=True)
    status = models.CharField("审批状态", max_length=20, choices=STATUS, default="PENDING")
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="approved_seals", verbose_name="审批人")
    approved_at = models.DateTimeField("审批时间", null=True, blank=True)
    approval = models.ForeignKey(Approval, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="seals", verbose_name="关联审批单")

    class Meta:
        verbose_name = "用印申请"
        verbose_name_plural = "用印申请"
        ordering = ["-created_at"]


class PerformancePlan(BaseModel):
    """绩效方案配置（支持分部门配置考核模板）"""
    name = models.CharField("方案名称", max_length=100)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="performance_plans", verbose_name="适用部门(空=全员)")
    cycle = models.CharField("考核周期", max_length=20, default="MONTH",
                             choices=[("MONTH", "月度"), ("QUARTER", "季度"), ("YEAR", "年度")])
    template = models.TextField("考核表(JSON/文本)", blank=True, help_text="分部门考核指标模板")
    is_active = models.BooleanField("启用", default=True)

    class Meta:
        verbose_name = "绩效方案"
        verbose_name_plural = "绩效方案"
        ordering = ["-is_active", "name"]


class PerformanceReview(BaseModel):
    """绩效考核：发起 / 评分 / 归档，结果写入员工人事档案"""
    STATUS = [("ONGOING", "进行中"), ("SUBMITTED", "已提交"), ("GRADED", "已评分"), ("ARCHIVED", "已归档")]
    plan = models.ForeignKey(PerformancePlan, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name="reviews", verbose_name="关联方案")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="performance_reviews", verbose_name="被考核人")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="reviewed_performances", verbose_name="考核人")
    period = models.CharField("考核周期(如 2026-Q3)", max_length=20)
    score = models.DecimalField("综合得分", max_digits=6, decimal_places=2, null=True, blank=True)
    grade = models.CharField("等级", max_length=10, blank=True)
    result = models.TextField("考核结果/评语", blank=True)
    status = models.CharField("状态", max_length=20, choices=STATUS, default="ONGOING")

    class Meta:
        verbose_name = "绩效考核"
        verbose_name_plural = "绩效考核"
        ordering = ["-created_at"]


class AddressBookVisibility(BaseModel):
    """通讯录可见权限：配置某角色能看到哪些部门人员"""
    name = models.CharField("规则名称", max_length=50)
    role = models.CharField("适用角色", max_length=20, choices=User.ROLE_CHOICES, blank=True)
    can_see_departments = models.ManyToManyField(Department, blank=True,
                                                 related_name="visible_rules", verbose_name="可查看部门")
    see_all = models.BooleanField("可看全公司", default=False)
    see_self_dept = models.BooleanField("仅看本部门", default=True)

    class Meta:
        verbose_name = "通讯录可见权限"
        verbose_name_plural = "通讯录可见权限"

    def __str__(self):
        return self.name


class RolePreset(BaseModel):
    """角色预设权限矩阵"""
    ROLE = [("SUPERADMIN", "超级管理员"), ("HR", "人事管理员"),
            ("MANAGER", "部门主管"), ("EMPLOYEE", "普通员工")]
    role = models.CharField("角色", max_length=20, choices=ROLE, unique=True)
    can_view_addressbook = models.BooleanField("查看通讯录", default=False)
    can_view_archives = models.BooleanField("查看人事档案", default=False)
    can_view_salary = models.BooleanField("查看薪资", default=False)
    can_view_contract = models.BooleanField("查看合同", default=False)
    can_view_performance = models.BooleanField("查看绩效", default=False)
    can_manage_attendance = models.BooleanField("管理考勤", default=False)
    can_approve = models.BooleanField("发起/审批", default=False)
    description = models.TextField("说明", blank=True)

    class Meta:
        verbose_name = "角色权限预设"
        verbose_name_plural = "角色权限预设"

    def __str__(self):
        return self.get_role_display()
