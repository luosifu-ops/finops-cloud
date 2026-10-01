"""入职培训：企业文化 / 制度 / 知识库 / 考试 / 入职资料"""
from django.db import models
from django.conf import settings
from apps.common.models import BaseModel


class CultureArticle(BaseModel):
    """企业文化：公司简介、愿景使命价值观、发展历程"""
    CATEGORY = [
        ("INTRO", "公司简介"),
        ("VISION", "愿景使命"),
        ("VALUE", "价值观"),
        ("HISTORY", "发展历程"),
        ("STORY", "员工故事"),
        ("MANAGE", "管理理念"),
    ]
    title = models.CharField("标题", max_length=200)
    category = models.CharField("分类", max_length=20, choices=CATEGORY, default="INTRO")
    cover = models.ImageField("封面图", upload_to="culture/", null=True, blank=True)
    content = models.TextField("正文内容", blank=True)
    video_url = models.CharField("视频链接", max_length=300, blank=True)
    is_published = models.BooleanField("已发布", default=True)
    sort = models.IntegerField("排序", default=0)
    view_count = models.IntegerField("阅读量", default=0)

    class Meta:
        verbose_name = "企业文化"
        verbose_name_plural = verbose_name
        ordering = ["sort", "-created_at"]

    def __str__(self):
        return self.title


class Regulation(BaseModel):
    """公司制度：考勤、薪酬、奖惩、保密、报销等"""
    CATEGORY = [
        ("ATTENDANCE", "考勤制度"),
        ("SALARY", "薪酬绩效"),
        ("REWARD", "奖惩制度"),
        ("SECRET", "保密与合规"),
        ("EXPENSE", "费用报销"),
        ("BEHAVIOR", "行为规范"),
        ("OTHER", "其他"),
    ]
    title = models.CharField("制度名称", max_length=200)
    category = models.CharField("分类", max_length=20, choices=CATEGORY, default="ATTENDANCE")
    version = models.CharField("版本号", max_length=20, default="V1.0")
    content = models.TextField("制度正文", blank=True)
    attachment = models.FileField("附件", upload_to="regulation/", null=True, blank=True)
    effective_date = models.DateField("生效日期", null=True, blank=True)
    is_published = models.BooleanField("已发布", default=True)
    must_read = models.BooleanField("要求已读确认", default=True)

    class Meta:
        verbose_name = "公司制度"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title}（{self.version}）"


class RegulationAck(models.Model):
    """制度已读确认记录"""
    regulation = models.ForeignKey(Regulation, on_delete=models.CASCADE, related_name="acks")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="regulation_acks")
    read_at = models.DateTimeField("已读时间", auto_now_add=True)

    class Meta:
        unique_together = ("regulation", "user")
        verbose_name = "制度已读确认"
        verbose_name_plural = verbose_name


class KnowledgeCategory(BaseModel):
    """财税知识库分类"""
    name = models.CharField("分类名称", max_length=50)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True,
        related_name="children", verbose_name="上级分类")
    sort = models.IntegerField("排序", default=0)

    class Meta:
        verbose_name = "知识分类"
        verbose_name_plural = verbose_name
        ordering = ["sort", "id"]

    def __str__(self):
        return self.name


class KnowledgeArticle(BaseModel):
    """知识库文章：代理记账 / 税务 / 工商 / 发票 / 社保 等"""
    LEVEL = [("BASIC", "入门"), ("MIDDLE", "进阶"), ("ADVANCED", "高阶")]
    CATEGORY = [
        ("AGENCY", "代理记账基础"),
        ("TAX", "税务知识"),
        ("INVOICE", "发票管理"),
        ("BUSINESS", "工商注册/变更/注销"),
        ("SOCIAL", "社保公积金"),
        ("LAW", "财税法规"),
        ("SOFTWARE", "做账软件操作"),
        ("SALE", "销售话术"),
        ("OPS", "投放运营"),
    ]
    title = models.CharField("标题", max_length=200)
    category = models.CharField("分类", max_length=20, choices=CATEGORY, default="AGENCY")
    knowledge_category = models.ForeignKey(
        KnowledgeCategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="articles", verbose_name="自定义分类")
    level = models.CharField("难度", max_length=20, choices=LEVEL, default="BASIC")
    summary = models.CharField("摘要", max_length=300, blank=True)
    content = models.TextField("正文", blank=True)
    video_url = models.CharField("视频链接", max_length=300, blank=True)
    attachment = models.FileField("课件附件", upload_to="knowledge/", null=True, blank=True)
    tags = models.CharField("标签(逗号分隔)", max_length=200, blank=True)
    is_published = models.BooleanField("已发布", default=True)
    is_required = models.BooleanField("必修", default=True)
    sort = models.IntegerField("排序", default=0)
    view_count = models.IntegerField("阅读量", default=0)

    class Meta:
        verbose_name = "知识文章"
        verbose_name_plural = verbose_name
        ordering = ["sort", "-created_at"]

    def __str__(self):
        return self.title


class LearningRecord(models.Model):
    """学习进度"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="learning_records")
    article = models.ForeignKey(KnowledgeArticle, on_delete=models.CASCADE, related_name="records")
    finished = models.BooleanField("已完成", default=False)
    duration = models.IntegerField("学习时长(秒)", default=0)
    last_at = models.DateTimeField("最近学习时间", auto_now=True)

    class Meta:
        unique_together = ("user", "article")
        verbose_name = "学习记录"
        verbose_name_plural = verbose_name


class QuestionBank(BaseModel):
    """题库分类"""
    name = models.CharField("题库名称", max_length=100)
    description = models.CharField("说明", max_length=300, blank=True)

    class Meta:
        verbose_name = "题库"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Question(BaseModel):
    TYPE = [
        ("SINGLE", "单选题"),
        ("MULTI", "多选题"),
        ("JUDGE", "判断题"),
        ("FILL", "填空题"),
        ("ESSAY", "简答题"),
    ]
    bank = models.ForeignKey(QuestionBank, on_delete=models.CASCADE, related_name="questions", verbose_name="题库")
    qtype = models.CharField("题型", max_length=20, choices=TYPE, default="SINGLE")
    stem = models.TextField("题干")
    options = models.JSONField("选项", default=list, blank=True,
                               help_text='格式：[{"key":"A","text":"选项内容"}]')
    answer = models.CharField("正确答案", max_length=200, help_text="单选A；多选AB；判断对/错")
    analysis = models.TextField("解析", blank=True)
    score = models.IntegerField("分值", default=5)
    level = models.CharField("难度", max_length=20, default="BASIC")

    class Meta:
        verbose_name = "题目"
        verbose_name_plural = verbose_name
        ordering = ["id"]

    def __str__(self):
        return f"[{self.get_qtype_display()}] {self.stem[:30]}"


class Exam(BaseModel):
    """考试"""
    STATUS = [("DRAFT", "草稿"), ("PUBLISHED", "已发布"), ("CLOSED", "已结束")]
    title = models.CharField("考试名称", max_length=200)
    description = models.TextField("说明", blank=True)
    bank = models.ForeignKey(QuestionBank, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="题库")
    question_count = models.IntegerField("抽题数量", default=20)
    total_score = models.IntegerField("总分", default=100)
    pass_score = models.IntegerField("及格分", default=60)
    duration = models.IntegerField("考试时长(分钟)", default=60)
    status = models.CharField("状态", max_length=20, choices=STATUS, default="DRAFT")
    start_at = models.DateTimeField("开放时间", null=True, blank=True)
    end_at = models.DateTimeField("截止时间", null=True, blank=True)
    allow_retake = models.BooleanField("允许重考", default=True)
    max_attempts = models.IntegerField("最大次数", default=3)

    class Meta:
        verbose_name = "考试"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class ExamRecord(models.Model):
    """考试记录"""
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="records")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="exam_records")
    score = models.DecimalField("得分", max_digits=6, decimal_places=2, default=0)
    passed = models.BooleanField("是否通过", default=False)
    answers = models.JSONField("作答详情", default=dict, blank=True)
    started_at = models.DateTimeField("开始时间", auto_now_add=True)
    submitted_at = models.DateTimeField("提交时间", null=True, blank=True)
    attempt = models.IntegerField("第几次", default=1)

    class Meta:
        verbose_name = "考试记录"
        verbose_name_plural = verbose_name
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.user}-{self.exam}-{self.score}"


class OnboardingProfile(BaseModel):
    """入职资料提交通道"""
    STATUS = [
        ("DRAFT", "待提交"),
        ("SUBMITTED", "待审核"),
        ("APPROVED", "已通过"),
        ("REJECTED", "已驳回"),
    ]
    EDUCATION = [("HIGH", "高中及以下"), ("COLLEGE", "大专"), ("BACHELOR", "本科"), ("MASTER", "硕士及以上")]

    name = models.CharField("姓名", max_length=50)
    phone = models.CharField("手机号", max_length=20)
    id_card_no = models.CharField("身份证号", max_length=30, blank=True)
    gender = models.CharField("性别", max_length=10, blank=True)
    birth_date = models.DateField("出生日期", null=True, blank=True)
    education = models.CharField("学历", max_length=20, choices=EDUCATION, default="COLLEGE")
    school = models.CharField("毕业院校", max_length=100, blank=True)
    address = models.CharField("家庭住址", max_length=200, blank=True)
    emergency_contact = models.CharField("紧急联系人", max_length=50, blank=True)
    emergency_phone = models.CharField("紧急联系电话", max_length=20, blank=True)
    bank_card_no = models.CharField("工资卡号", max_length=40, blank=True)

    department = models.ForeignKey(
        "accounts.Department", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="拟入职部门")
    position = models.CharField("拟任岗位", max_length=50, blank=True)
    entry_date = models.DateField("预计入职日期", null=True, blank=True)

    id_card_front = models.ImageField("身份证人像面", upload_to="onboarding/", null=True, blank=True)
    id_card_back = models.ImageField("身份证国徽面", upload_to="onboarding/", null=True, blank=True)
    diploma = models.ImageField("学历证书", upload_to="onboarding/", null=True, blank=True)
    bank_card_img = models.ImageField("银行卡照片", upload_to="onboarding/", null=True, blank=True)
    photo = models.ImageField("一寸照片", upload_to="onboarding/", null=True, blank=True)
    resume = models.FileField("简历附件", upload_to="onboarding/", null=True, blank=True)
    other_files = models.JSONField("其他资料", default=list, blank=True)

    status = models.CharField("状态", max_length=20, choices=STATUS, default="DRAFT")
    review_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_onboardings", verbose_name="审核人")
    review_at = models.DateTimeField("审核时间", null=True, blank=True)
    review_remark = models.TextField("审核意见", blank=True)
    bound_user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="onboarding_profile", verbose_name="已转正式员工")

    class Meta:
        verbose_name = "入职资料"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name}-{self.get_status_display()}"


class OnboardingTask(BaseModel):
    """新人入职任务清单（制度已读、课程学习、考试、资料提交）"""
    TASK_TYPE = [
        ("REGULATION", "阅读制度"),
        ("COURSE", "学习课程"),
        ("EXAM", "通过考试"),
        ("MATERIAL", "提交资料"),
        ("OTHER", "其他事项"),
    ]
    title = models.CharField("任务名称", max_length=200)
    task_type = models.CharField("任务类型", max_length=20, choices=TASK_TYPE, default="OTHER")
    description = models.TextField("任务说明", blank=True)
    regulation = models.ForeignKey(Regulation, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="关联制度")
    article = models.ForeignKey(KnowledgeArticle, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="关联课程")
    exam = models.ForeignKey(Exam, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="关联考试")
    due_days = models.IntegerField("入职后需完成天数", default=7)
    required = models.BooleanField("必修任务", default=True)
    sort = models.IntegerField("排序", default=0)

    class Meta:
        verbose_name = "入职任务"
        verbose_name_plural = verbose_name
        ordering = ["sort", "id"]

    def __str__(self):
        return self.title


class OnboardingTaskRecord(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="onboarding_tasks")
    task = models.ForeignKey(OnboardingTask, on_delete=models.CASCADE, related_name="records")
    finished = models.BooleanField("已完成", default=False)
    finished_at = models.DateTimeField("完成时间", null=True, blank=True)

    class Meta:
        unique_together = ("user", "task")
        verbose_name = "入职任务完成记录"
        verbose_name_plural = verbose_name
