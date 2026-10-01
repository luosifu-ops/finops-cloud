"""增长中心路由（纯新增，挂载在 /api/growth/ 下）"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .viewsets import (
    LeadChannelViewSet, LeadExtViewSet, LeadPoolViewSet, LeadFlowViewSet,
    FieldTaskViewSet, FieldProgressViewSet,
    ValueAddedProjectViewSet, AdSpendRecordViewSet, GrowthRoleViewSet,
    CloserChannelViewSet, LeadFollowUpViewSet, FieldTaskNodeViewSet,
)
from .stats import GrowthStatsViewSet

router = DefaultRouter()
router.register("channels", LeadChannelViewSet, basename="growth-channel")
router.register("leads", LeadExtViewSet, basename="growth-lead")
router.register("pool", LeadPoolViewSet, basename="growth-pool")
router.register("flows", LeadFlowViewSet, basename="growth-flow")
router.register("field-tasks", FieldTaskViewSet, basename="growth-fieldtask")
router.register("field-progress", FieldProgressViewSet, basename="growth-fieldprogress")
router.register("field-nodes", FieldTaskNodeViewSet, basename="growth-fieldnode")
router.register("followups", LeadFollowUpViewSet, basename="growth-followup")
router.register("value-added", ValueAddedProjectViewSet, basename="growth-vaproject")
router.register("ad-spend", AdSpendRecordViewSet, basename="growth-adspend")
router.register("roles", GrowthRoleViewSet, basename="growth-role")
router.register("closer-channels", CloserChannelViewSet, basename="growth-closerchannel")
router.register("stats", GrowthStatsViewSet, basename="growth-stats")

urlpatterns = [
    path("", include(router.urls)),
]
