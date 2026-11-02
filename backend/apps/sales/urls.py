from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import viewsets

router = DefaultRouter()
router.register("leads", viewsets.LeadViewSet, basename="lead")
router.register("customers", viewsets.CustomerViewSet, basename="customer")
router.register("contracts", viewsets.ContractViewSet, basename="contract")
router.register("call-records", viewsets.CallRecordViewSet, basename="call-record")
router.register("followups", viewsets.FollowUpViewSet, basename="followup")
router.register("targets", viewsets.SalesTargetViewSet, basename="sales-target")
router.register("commission-rules", viewsets.CommissionRuleViewSet, basename="commission-rule")
router.register("salary", viewsets.SalaryViewSet, basename="salary")
router.register("streamers", viewsets.StreamerViewSet, basename="streamer")
router.register("customer-tags", viewsets.CustomerTagViewSet, basename="customer-tag")

urlpatterns = [
    path("", include(router.urls)),
]
