"""公司通知公告：路由"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import viewsets

router = DefaultRouter()
router.register("", viewsets.AnnouncementViewSet, basename="announcement")

urlpatterns = [
    path("", include(router.urls)),
]
