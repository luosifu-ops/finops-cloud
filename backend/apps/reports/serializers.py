"""工作汇报模块序列化器"""
from rest_framework import serializers
from .models import (
    ReportTemplate, DailyReport, WeeklyReport, MonthlyReport, ReviewReport, ReportComment,
    TeamSummary,
)


class ReportTemplateSerializer(serializers.ModelSerializer):
    """汇报模板"""
    kind_name = serializers.CharField(source="get_kind_display", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = ReportTemplate
        fields = ["id", "name", "kind", "kind_name", "department", "department_name",
                  "fields", "is_default", "created_at"]


class DailyReportSerializer(serializers.ModelSerializer):
    """日报"""
    user_name = serializers.CharField(source="user.display_name", read_only=True)
    department_name = serializers.CharField(source="user.department.name", read_only=True)
    status_name = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = DailyReport
        fields = ["id", "user", "user_name", "department_name", "date",
                  "today_done", "today_data", "problems", "tomorrow_plan",
                  "need_help", "remark", "status", "status_name",
                  "submitted_at", "score", "created_at"]
        read_only_fields = ["user", "submitted_at", "created_at"]


class WeeklyReportSerializer(serializers.ModelSerializer):
    """周报"""
    user_name = serializers.CharField(source="user.display_name", read_only=True)
    department_name = serializers.CharField(source="user.department.name", read_only=True)

    class Meta:
        model = WeeklyReport
        fields = ["id", "user", "user_name", "department_name", "year", "week",
                  "start_date", "end_date", "summary", "data", "next_plan",
                  "problems", "submitted_at", "score", "created_at"]
        read_only_fields = ["user", "submitted_at", "created_at"]


class MonthlyReportSerializer(serializers.ModelSerializer):
    """月报"""
    user_name = serializers.CharField(source="user.display_name", read_only=True)
    department_name = serializers.CharField(source="user.department.name", read_only=True)
    completion = serializers.ReadOnlyField()

    class Meta:
        model = MonthlyReport
        fields = ["id", "user", "user_name", "department_name", "month",
                  "summary", "data", "performance", "target", "completion",
                  "next_plan", "self_review", "submitted_at", "score", "created_at"]
        read_only_fields = ["user", "submitted_at", "created_at"]


class ReviewReportSerializer(serializers.ModelSerializer):
    """专项复盘"""
    user_name = serializers.CharField(source="user.display_name", read_only=True)
    department_name = serializers.CharField(source="user.department.name", read_only=True)
    kind_name = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = ReviewReport
        fields = ["id", "user", "user_name", "department_name", "kind", "kind_name",
                  "title", "background", "process", "cause", "improvement",
                  "action_plan", "submitted_at", "created_at"]
        read_only_fields = ["user", "submitted_at", "created_at"]


class TeamSummarySerializer(serializers.ModelSerializer):
    """团队汇总（content 可编辑，其余字段由系统自动汇总）"""
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    team_name = serializers.CharField(source="team.name", read_only=True)
    period_label = serializers.ReadOnlyField()
    edited_by_name = serializers.SerializerMethodField()

    class Meta:
        model = TeamSummary
        fields = ["id", "kind", "kind_label", "period", "period_label",
                  "department", "department_name", "team", "team_name",
                  "title", "content", "stats", "member_total", "submitted_total",
                  "source_ids", "is_edited", "edited_by", "edited_by_name", "edited_at",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "kind", "period", "department", "team",
                            "stats", "member_total", "submitted_total", "source_ids",
                            "edited_by", "edited_at", "created_at", "updated_at"]

    def get_edited_by_name(self, obj):
        u = obj.edited_by
        return (getattr(u, "display_name", None) or getattr(u, "username", "")) if u else ""


class ReportCommentSerializer(serializers.ModelSerializer):
    """汇报点评"""
    commenter_name = serializers.CharField(source="commenter.display_name", read_only=True)
    content_type_name = serializers.CharField(source="get_content_type_display", read_only=True)

    class Meta:
        model = ReportComment
        fields = ["id", "content_type", "content_type_name", "object_id",
                  "commenter", "commenter_name", "content", "created_at"]
        read_only_fields = ["commenter", "created_at"]
