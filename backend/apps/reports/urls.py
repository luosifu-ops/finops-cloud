from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import viewsets

router = DefaultRouter()
router.register("report-templates", viewsets.ReportTemplateViewSet, basename="report-template")
router.register("daily-reports", viewsets.DailyReportViewSet, basename="daily-report")
router.register("weekly-reports", viewsets.WeeklyReportViewSet, basename="weekly-report")
router.register("monthly-reports", viewsets.MonthlyReportViewSet, basename="monthly-report")
router.register("review-reports", viewsets.ReviewReportViewSet, basename="review-report")
router.register("report-comments", viewsets.ReportCommentViewSet, basename="report-comment")
router.register("team-summaries", viewsets.TeamSummaryViewSet, basename="team-summary")

urlpatterns = [
    path("", include(router.urls)),
]
