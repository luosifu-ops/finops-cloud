"""公司通知公告：发布通知 / 发布文件 / 已读回执"""
from django.db import models

from apps.common.models import BaseModel
from apps.accounts.models import User


class Announcement(BaseModel):
    """公司通知公告：全员可见，可附文件，支持已读回执（接收确认）"""
    CATEGORY = (
        ("NOTICE", "通知"),
        ("ANNOUNCEMENT", "公告"),
        ("FILE", "文件发布"),
        ("MEETING", "会议安排"),
    )
    title = models.CharField("标题", max_length=200)
    content = models.TextField("正文", blank=True, default="")
    category = models.CharField("类型", max_length=20, choices=CATEGORY, default="NOTICE")
    # 发布文件（如红头文件、制度附件、会议材料）
    file = models.FileField("附件文件", upload_to="notices/", null=True, blank=True)
    file_name = models.CharField("原始文件名", max_length=255, blank=True, default="")
    # 置顶：优先展示
    pinned = models.BooleanField("置顶", default=False)
    # 已读（接收）人员：员工点「确认接收」即写入
    read_by = models.ManyToManyField(
        User, blank=True, related_name="read_announcements", verbose_name="已读人员"
    )

    class Meta:
        ordering = ["-pinned", "-created_at"]
        verbose_name = "通知公告"
        verbose_name_plural = "通知公告"

    def __str__(self):
        return self.title
