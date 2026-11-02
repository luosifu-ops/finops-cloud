"""组织与账号：部门 / 小组 / 岗位 / 员工"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.common.models import BaseModel


class Department(BaseModel):
    # 2026-10-28 放开：原 code 为 4 个固定枚举，导致无法新增自定义部门；
    # 现改为自由编码，SALES/ACCOUNT/OPS/MGMT 四个保留为业务代码（菜单分组/数据权限依赖它们，不可占用）
    RESERVED_CODES = ["SALES", "ACCOUNT", "OPS", "MGMT"]
    name = models.CharField("部门名称", max_length=50)
    code = models.CharField(
        "部门编码", max_length=20, unique=True,
        help_text="业务编码，如 SALES/ACCOUNT/OPS/MGMT；自定义部门可用如 FIN/RISK 等")
    leader = models.ForeignKey(
        "User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="led_departments", verbose_name="部门负责人",
    )
    description = models.TextField("部门职责", blank=True)
    order = models.IntegerField("排序", default=0)
    # 2026-09-12 增量：钉钉式组织架构层级（上级部门，支持多级树）
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="children", verbose_name="上级部门")
    # 2026-09-12 增量：钉钉通讯录部门扩展字段（不影响原有树结构与数据）
    dept_no = models.CharField("部门编号", max_length=30, blank=True, default="")
    founded_date = models.DateField("成立时间", null=True, blank=True)
    remark = models.TextField("部门备注", blank=True, default="")
    is_virtual = models.BooleanField("虚拟部门(不计编制)", default=False,
                                     help_text="用于临时项目组、专项小组，不计入正式编制")
    vice_leaders = models.ManyToManyField(
        "User", blank=True, related_name="vice_led_departments", verbose_name="副主管")

    class Meta:
        verbose_name = "部门"
        verbose_name_plural = verbose_name
        ordering = ["order", "id"]

    def __str__(self):
        return self.name


class Team(BaseModel):
    """部门下的小组（如电销一组、二组）"""
    name = models.CharField("小组名称", max_length=50)
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="teams", verbose_name="所属部门")
    leader = models.ForeignKey(
        "User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="led_teams", verbose_name="组长")
    month_target = models.DecimalField("月度目标(元)", max_digits=14, decimal_places=2, default=0)

    class Meta:
        verbose_name = "小组"
        verbose_name_plural = verbose_name
        ordering = ["id"]

    def __str__(self):
        return f"{self.department.name}-{self.name}"


class Position(BaseModel):
    name = models.CharField("岗位名称", max_length=50)
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="positions", verbose_name="所属部门")
    description = models.TextField("岗位职责", blank=True)

    class Meta:
        verbose_name = "岗位"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class User(AbstractUser):
    """员工账号：一个 Django 用户 = 一个员工"""
    ROLE_CHOICES = [
        ("BOSS", "老板/总经理"),
        ("MANAGER", "部门经理"),
        ("LEADER", "组长/主管"),
        ("EMPLOYEE", "员工"),
        ("HR", "人事行政"),
    ]
    STATUS_CHOICES = [
        ("PROBATION", "试用期"),
        ("REGULAR", "正式"),
        ("INTERN", "实习"),
        ("RESIGNED", "已离职"),
    ]

    phone = models.CharField("手机号", max_length=20, blank=True, unique=True, null=True)
    avatar = models.ImageField("头像", upload_to="avatar/", null=True, blank=True)
    employee_no = models.CharField("工号", max_length=30, blank=True, unique=True, null=True)

    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="members", verbose_name="所属部门")
    team = models.ForeignKey(
        Team, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="members", verbose_name="所属小组")
    position = models.ForeignKey(
        Position, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="members", verbose_name="岗位")
    # 2026-09-12 增量：钉钉员工档案扩展字段（职级序列）
    job_level = models.ForeignKey(
        "hr.JobLevel", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="members", verbose_name="职级序列")
    role = models.CharField("角色", max_length=20, choices=ROLE_CHOICES, default="EMPLOYEE")
    status = models.CharField("在职状态", max_length=20, choices=STATUS_CHOICES, default="PROBATION")

    entry_date = models.DateField("入职日期", null=True, blank=True)
    regular_date = models.DateField("转正日期", null=True, blank=True)
    probation_end = models.DateField("试用期到期", null=True, blank=True)
    leave_date = models.DateField("离职日期", null=True, blank=True)

    id_card_no = models.CharField("身份证号", max_length=30, blank=True)
    bank_card_no = models.CharField("工资卡号", max_length=40, blank=True)
    base_salary = models.DecimalField("底薪(元/月)", max_digits=12, decimal_places=2, default=0,
                                      help_text="用于工资自动核算")
    address = models.CharField("现住址", max_length=200, blank=True)
    emergency_contact = models.CharField("紧急联系人", max_length=50, blank=True)
    emergency_phone = models.CharField("紧急联系电话", max_length=20, blank=True)

    month_target = models.DecimalField("个人月度业绩目标(元)", max_digits=14, decimal_places=2, default=0)
    openid = models.CharField("微信openid(小程序)", max_length=64, blank=True, db_index=True)
    wx_unionid = models.CharField("微信unionid(开放平台)", max_length=64, blank=True, db_index=True)
    wx_web_openid = models.CharField("微信openid(网站应用)", max_length=64, blank=True, db_index=True)
    wx_nickname = models.CharField("微信昵称", max_length=64, blank=True)
    wx_avatar = models.URLField("微信头像", blank=True, max_length=512)

    groups = models.ManyToManyField(
        "auth.Group", related_name="account_users", blank=True,
        verbose_name="权限组", help_text="系统权限组")
    user_permissions = models.ManyToManyField(
        "auth.Permission", related_name="account_user_perms", blank=True, verbose_name="用户权限")

    class Meta:
        verbose_name = "员工"
        verbose_name_plural = verbose_name
        ordering = ["department", "id"]

    def __str__(self):
        return f"{self.get_full_name() or self.username}"

    # ---------- 员工编号（工号）自动生成 ----------
    # 规则：EMP + 4 位序号（EMP0001 起），按库中现有最大号递增；
    # 生成逻辑放在 save() 里，保证「新增员工 / 批量导入 / 入职审批 / 创建账号」等
    # 所有入口都会自动带号，避免某条链路漏号导致列表出现空工号。
    EMPLOYEE_NO_PREFIX = "EMP"

    @classmethod
    def next_employee_no(cls):
        """取下一个可用员工编号（不改库，仅计算）"""
        prefix = cls.EMPLOYEE_NO_PREFIX
        max_no = 0
        rows = cls.objects.filter(
            employee_no__startswith=prefix).values_list("employee_no", flat=True)
        for no in rows:
            tail = str(no or "")[len(prefix):]
            if tail.isdigit():
                max_no = max(max_no, int(tail))
        return f"{prefix}{max_no + 1:04d}"

    def save(self, *args, **kwargs):
        if not self.employee_no:
            if self.pk:
                # 编辑保存时若前端把工号清空，沿用库中已有编号，避免"改一次换一个号"
                prev = type(self).objects.filter(pk=self.pk).values_list(
                    "employee_no", flat=True).first()
                self.employee_no = prev or type(self).next_employee_no()
            else:
                self.employee_no = type(self).next_employee_no()
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    @property
    def dept_name(self):
        return self.department.name if self.department else "-"

    @property
    def is_boss(self):
        return self.role == "BOSS" or self.is_superuser

    @property
    def is_manager(self):
        return self.role in ("BOSS", "MANAGER")

    @property
    def is_leader(self):
        return self.role in ("BOSS", "MANAGER", "LEADER")


class OperationLog(models.Model):
    """操作日志：谁在什么时间做了什么"""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="操作人")
    module = models.CharField("模块", max_length=50)
    action = models.CharField("动作", max_length=50)
    detail = models.TextField("详情", blank=True)
    ip = models.GenericIPAddressField("IP", null=True, blank=True)
    created_at = models.DateTimeField("时间", auto_now_add=True)

    class Meta:
        verbose_name = "操作日志"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} {self.action} {self.module}"


class PhoneVerifyCode(models.Model):
    """手机号登录验证码

    演示/自建环境：未配置短信网关时，验证码通过接口返回给前端（debug_code）并在日志打印；
    配置 SMS_API_KEY 后可对接真实短信服务商（网关调用处统一在 services 层扩展）。
    """
    SCENE = [("LOGIN", "登录"), ("BIND", "绑定手机号"), ("RESET", "重置密码")]
    phone = models.CharField("手机号", max_length=20, db_index=True)
    code = models.CharField("验证码", max_length=10)
    scene = models.CharField("场景", max_length=20, choices=SCENE, default="LOGIN")
    used = models.BooleanField("已使用", default=False)
    ip = models.CharField("请求IP", max_length=64, blank=True)
    expire_at = models.DateTimeField("过期时间")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "手机验证码"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.phone}-{self.code}-{self.scene}"


class CompanyProfile(BaseModel):
    """公司简介与联系方式（企查查信息），单例：全公司仅一条"""
    name = models.CharField("公司全称", max_length=200, default="")
    short_name = models.CharField("简称", max_length=100, blank=True)
    credit_code = models.CharField("统一社会信用代码", max_length=50, blank=True)
    legal_person = models.CharField("法定代表人", max_length=50, blank=True)
    registered_capital = models.CharField("注册资本", max_length=50, blank=True)
    established_date = models.CharField("成立日期", max_length=30, blank=True)
    business_scope = models.TextField("经营范围", blank=True)
    intro = models.TextField("公司简介", blank=True)
    culture = models.TextField("企业文化", blank=True)
    address = models.CharField("注册地址", max_length=300, blank=True)
    phone = models.CharField("联系电话", max_length=50, blank=True)
    email = models.CharField("邮箱", max_length=100, blank=True)
    wechat = models.CharField("微信/客服", max_length=100, blank=True)
    website = models.CharField("官网", max_length=200, blank=True)
    qcc_screenshot = models.URLField("企查查截图URL", blank=True, max_length=512)
    logo = models.URLField("Logo URL", blank=True, max_length=512)

    class Meta:
        verbose_name = "公司简介"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name or "公司简介"


# ----------------------------------------------------------------------------
# 钉钉式组织架构 · 部门 / 岗位独立制度 + 入职申请流（2026-09-12 增量）
# ----------------------------------------------------------------------------
class DeptRule(BaseModel):
    """部门 / 岗位独立考勤 / 考核制度（管理员可自主配置）"""
    RULE_TYPE = [
        ("ATTENDANCE", "考勤制度"),
        ("ASSESSMENT", "考核制度"),
    ]
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="rules", verbose_name="所属部门")
    position = models.ForeignKey(
        Position, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="rules", verbose_name="适用岗位(可选)")
    rule_type = models.CharField("制度类型", max_length=20, choices=RULE_TYPE, default="ATTENDANCE")
    title = models.CharField("制度标题", max_length=100)
    content = models.TextField("制度内容", blank=True)

    class Meta:
        verbose_name = "部门制度"
        verbose_name_plural = "部门制度"
        ordering = ["department", "rule_type", "id"]

    def __str__(self):
        return f"{self.department.name}-{self.get_rule_type_display()}-{self.title}"


class EntryApplication(BaseModel):
    """入职申请：员工提交资料 → 人事管理员审核 → 归类部门岗位并继承制度"""
    STATUS = [
        ("PENDING", "待审核"),
        ("APPROVED", "已通过"),
        ("REJECTED", "已拒绝"),
    ]
    applicant_name = models.CharField("申请人姓名", max_length=50)
    phone = models.CharField("联系电话", max_length=20, blank=True, default="")
    id_card_no = models.CharField("身份证号", max_length=30, blank=True, default="")
    # 员工申请时自设登录密码（只存哈希，永不回传）。审核通过直接作为账号初始密码，
    # 废除历史上"全员统一初始密码 finops123456"的做法（2026-10-28 Boss 体检指示）。
    password_hash = models.CharField("登录密码(哈希)", max_length=128, blank=True, default="")
    proposed_department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="entry_applications", verbose_name="意向部门")
    proposed_position = models.ForeignKey(
        Position, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="entry_applications", verbose_name="意向岗位")
    expected_salary = models.DecimalField("期望薪资(元/月)", max_digits=12, decimal_places=2, default=0)
    resume = models.FileField("简历/资料附件", upload_to="entry/", null=True, blank=True)
    status = models.CharField("状态", max_length=20, choices=STATUS, default="PENDING")
    reviewed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_entries", verbose_name="审核人")
    reviewed_at = models.DateTimeField("审核时间", null=True, blank=True)
    reject_reason = models.CharField("拒绝原因", max_length=300, blank=True, default="")
    remark = models.TextField("备注", blank=True, default="")

    class Meta:
        verbose_name = "入职申请"
        verbose_name_plural = "入职申请"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.applicant_name}-{self.get_status_display()}"
