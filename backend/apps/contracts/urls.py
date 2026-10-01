"""合同订单名录路由（挂载在 /api/contracts/ 下）"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import ContractRecordViewSet

router = DefaultRouter()
router.register("records", ContractRecordViewSet, basename="contract-record")

urlpatterns = [
    path("", include(router.urls)),
]
