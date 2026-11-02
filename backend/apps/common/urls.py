from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api

router = DefaultRouter()
router.register("op-logs", api.OperationLogViewSet, basename="op-log")
router.register("inbox", api.InboxViewSet, basename="inbox")

urlpatterns = [
    path("", include(router.urls)),
    path("sys-config/", api.sys_config_view, name="sys-config"),
]
