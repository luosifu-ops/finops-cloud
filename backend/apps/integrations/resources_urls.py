"""系统资源对接配置路由（纯新增）"""
from rest_framework.routers import DefaultRouter

from .resources_views import CloudResourceConfigViewSet

router = DefaultRouter()
router.register("resources", CloudResourceConfigViewSet, basename="integration-resource")
