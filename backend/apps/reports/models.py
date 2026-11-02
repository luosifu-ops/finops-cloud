"""工作汇报：日报 / 周报 / 月报 / 复盘"""
from django.db import models
from django.conf import settings
from apps.common.models import BaseModel


class ReportTemplate(BaseModel):
    """汇报模板"""
    KIND = [("DAILY", "日报"), ("WEEKLY", "周报"), ("MONTHLY", "月报"), ("REVIEW", "复盘")]
    name = models.CharField("模板名称", max_length=100)
    kind = models.CharField("类型", max_length=20, choices=KIND, default="DAILY")
    department = models.ForeignKey("accounts.Department", on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name="适用部门")
    fields = models.JSONField("字段配置", default=list, blank=True,
                              help_text='[{"key":"today","label":"今日完成","type":"textarea","required":true}]')
    is_default = models.BooleanField("默认模板", default=False)

    class Meta:
        verbose_name = "汇报模板"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class DailyReport(BaseModel):
    """日报"""
    STATUS = [("DRAFT", "草稿"), ("SUBMITTED", "已提交"), ("REVIEWED", "已点评")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="daily_reports", verbose_name="员工")
    date = models.DateField("日期", db_index=True)
    today_done = models.TextField("今日完成", blank=True)
    today_data = models.JSONField("今日数据", default=dict, blank=True,
                                  help_text='如 {"calls":80,"wechat":12,"deal":1}')
    problems = models.TextField("遇到问题", blank=True)
    tomorrow_plan = models.TextField("明日计划", blank=True)
    need_help = models.TextField("需要支持", blank=True)
    remark = models.TextField("其他", blank=True)
    status = models.CharField("状态", max_length=20, choices=STATUS, default="DRAFT")
    submitted_at = models.DateTimeField("提交时间", null=True, blank=True)
    score = models.IntegerField("主管评分", null=True, blank=True)

    class Meta:
        verbose_name = "日报"
        verbose_name_plural = verbose_name
        unique_together = ("user", "date")
        ordering = ["-date"]


class WeeklyReport(BaseModel):
    """周报"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="weekly_reports", verbose_name="员工")
    year = models.IntegerField("年")
    week = models.IntegerField("第几周")
    start_date = models.DateField("开始日期")
    end_date = models.DateField("结束日期")
    summary = models.TextField("本周总结", blank=True)
    data = models.JSONField("本周数据", default=dict, blank=True)
    next_plan = models.TextField("下周计划", blank=True)
    problems = models.TextField("问题与建议", blank=True)
    submitted_at = models.DateTimeField("提交时间", null=True, blank=True)
    score = models.IntegerField("主管评分", null=True, blank=True)

    class Meta:
        verbose_name = "周报"
        verbose_name_plural = verbose_name
        ordering = ["-year", "-week"]
        unique_together = ("user", "year", "week")


class MonthlyReport(BaseModel):
    """月报"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="monthly_reports", verbose_name="员工")
    month = models.CharField("月份", max_length=7, db_index=True)  # 2026-09
    summary = models.TextField("本月总结", blank=True)
    data = models.JSONField("本月数据", default=dict, blank=True)
    performance = models.DecimalField("业绩金额", max_digits=14, decimal_places=2, default=0)
    target = models.DecimalField("目标金额", max_digits=14, decimal_places=2, default=0)
    next_plan = models.TextField("下月计划", blank=True)
    self_review = models.TextField("自我复盘", blank=True)
    submitted_at = models.DateTimeField("提交时间", null=True, blank=True)
    score = models.IntegerField("主管评分", null=True, blank=True)

    class Meta:
        verbose_name = "月报"
        verbose_name_plural = verbose_name
        ordering = ["-month"]
        unique_together = ("user", "month")

    @property
    def completion(self):
        if self.target and self.target > 0:
            return round(float(self.performance) / float(self.target) * 100, 1)
        return 0


class ReviewReport(BaseModel):
    """专项复盘（如丢单复盘、客户投诉复盘、活动复盘）"""
    KIND = [("LOSE", "丢单复盘"), ("COMPLAINT", "投诉复盘"), ("ACTIVITY", "活动复盘"),
            ("PROJECT", "项目复盘"), ("PERSONAL", "个人复盘"), ("OTHER", "其他")]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="reviews", verbose_name="复盘人")
    kind = models.CharField("复盘类型", max_length=20, choices=KIND, default="OTHER")
    title = models.CharField("复盘主题", max_length=200)
    background = models.TextField("背景", blank=True)
    process = models.TextField("过程还原", blank=True)
    cause = models.TextField("原因分析", blank=True)
    improvement = models.TextField("改进措施", blank=True)
    action_plan = models.JSONField("行动计划", default=list, blank=True,
                                   help_text='[{"item":"动作","owner":"负责人","deadline":"2026-09-10"}]')
    submitted_at = models.DateTimeField("提交时间", null=True, blank=True)

    class Meta:
        verbose_name = "复盘报告"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]


class TeamSummary(BaseModel):
    """团队汇总（2026-10-30 新增）

    员工提交日报 / 周报 / 月报后，系统按「部门（可细化到小组）+ 周期」自动重建汇总正文；
    主管可在「团队汇报 → 团队汇总」直接编辑修改汇总内容（编辑后标记 is_edited，
    后续自动汇总只更新统计，不再覆盖人工润色过的正文）。
    """
    KIND = [("DAILY", "日报汇总"), ("WEEKLY", "周报汇总"), ("MONTHLY", "月报汇总")]
    kind = models.CharField("汇总类型", max_length=20, choices=KIND, default="DAILY")
    period = models.CharField("周期", max_length=20, db_index=True,
                              help_text="日报 2026-10-30 / 周报 2026-W44 / 月报 2026-10")
    department = models.ForeignKey("accounts.Department", on_delete=models.CASCADE,
                                   null=True, blank=True, related_name="team_summaries",
                                   verbose_name="所属部门")
    team = models.ForeignKey("accounts.Team", on_delete=models.SET_NULL,
                             null=True, blank=True, related_name="team_summaries",
                             verbose_name="所属小组")
    title = models.CharField("汇总标题", max_length=200, blank=True)
    content = models.TextField("汇总内容", blank=True)
    stats = models.JSONField("汇总统计", default=dict, blank=True)
    member_total = models.IntegerField("在职人数", default=0)
    submitted_total = models.IntegerField("已提交人数", default=0)
    source_ids = models.JSONField("来源汇报ID", default=list, blank=True)
    is_edited = models.BooleanField("已人工编辑", default=False)
    edited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                  null=True, blank=True,
                                  related_name="edited_team_summaries", verbose_name="最后编辑人")
    edited_at = models.DateTimeField("最后编辑时间", null=True, blank=True)

    class Meta:
        verbose_name = "团队汇总"
        verbose_name_plural = verbose_name
        ordering = ["-period", "kind"]
        unique_together = ("kind", "period", "department", "team")

    @property
    def period_label(self):
        if self.kind == "WEEKLY" and "-W" in (self.period or ""):
            y, w = self.period.split("-W")
            return f"{y} 年第 {int(w)} 周"
        if self.kind == "MONTHLY" and len(self.period or "") == 7:
            return f"{self.period[:4]} 年 {int(self.period[5:])} 月"
        return self.period or ""

    def __str__(self):
        return f"{self.get_kind_display()}-{self.period}-{self.department_id or '全部'}"


class ReportComment(models.Model):
    """汇报点评"""
    CONTENT_TYPE = [("DAILY", "日报"), ("WEEKLY", "周报"), ("MONTHLY", "月报"), ("REVIEW", "复盘")]
    content_type = models.CharField("类型", max_length=20, choices=CONTENT_TYPE, default="DAILY")
    object_id = models.IntegerField("对象ID")
    commenter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                  related_name="report_comments", verbose_name="点评人")
    content = models.TextField("点评内容")
    created_at = models.DateTimeField("点评时间", auto_now_add=True)

    class Meta:
        verbose_name = "汇报点评"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
