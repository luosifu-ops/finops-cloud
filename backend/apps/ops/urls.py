"""运营部：路由"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import viewsets

router = DefaultRouter()
router.register("platforms", viewsets.AdPlatformViewSet, basename="ad-platform")
router.register("accounts", viewsets.AdAccountViewSet, basename="ad-account")
router.register("campaigns", viewsets.AdCampaignViewSet, basename="ad-campaign")
router.register("daily-stats", viewsets.AdDailyStatViewSet, basename="ad-daily-stat")
router.register("creatives", viewsets.AdCreativeViewSet, basename="ad-creative")
router.register("content-posts", viewsets.ContentPostViewSet, basename="content-post")
router.register("content-stats", viewsets.ContentStatViewSet, basename="content-stat")
router.register("budgets", viewsets.ChannelBudgetViewSet, basename="channel-budget")
router.register("daily-reports", viewsets.OpsDailyReportViewSet, basename="ops-daily-report")
router.register("anchor-daily-reports", viewsets.AnchorDailyReportViewSet, basename="anchor-daily-report")
router.register("lead-ledgers", viewsets.LeadLedgerViewSet, basename="lead-ledger")
router.register("anchor-ad-stats", viewsets.AnchorAdStatViewSet, basename="anchor-ad-stat")

urlpatterns = [
    path("", include(router.urls)),
]
router.register("cost-records", viewsets.CostRecordViewSet, basename="cost-record")
