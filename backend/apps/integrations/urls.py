from django.urls import path, include
from . import views
from .resources_urls import router as resource_router

urlpatterns = [
    path("enterprise/search/", views.enterprise_search, name="enterprise-search"),
    path("enterprise/<str:credit_code>/", views.enterprise_detail, name="enterprise-detail"),
    path("douyin/account/", views.douyin_account, name="douyin-account"),
    path("benchmark/platforms/", views.benchmark_platforms, name="benchmark-platforms"),
    path("benchmark/search/", views.benchmark_search, name="benchmark-search"),
    path("yunzhangfang/overview/", views.yunzhangfang_overview, name="yunzhangfang-overview"),
    path("training/videos/", views.training_video_list, name="training-video-list"),
    path("training/videos/<int:pk>/", views.training_video_detail, name="training-video-detail"),
    # --- 纯新增：系统资源对接配置（域名/存储/服务器 直连官方） ---
    path("", include(resource_router.urls)),
    # --- 钉钉通讯录同步（2026-10-28 增量，仅老板/人事） ---
    path("dingtalk/status/", views.dingtalk_status, name="dingtalk-status"),
    path("dingtalk/sync/", views.dingtalk_sync, name="dingtalk-sync"),
]

# --- 对标账号库（2026-11-02 Boss 指示：自建账号库，全员可录入可检索） ---
from rest_framework.routers import DefaultRouter
from .viewsets import BenchmarkAccountViewSet

benchmark_router = DefaultRouter()
benchmark_router.register("benchmark-accounts", BenchmarkAccountViewSet, basename="benchmark-account")
urlpatterns += [path("", include(benchmark_router.urls))]
