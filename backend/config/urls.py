"""财税企管云 · 全局路由
统一 API 前缀：/api/<模块>/
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve as media_serve
from rest_framework_simplejwt.views import TokenRefreshView
from config.jwt_auth import set_auth_cookies
from config.branding import branding_view


class CookieTokenRefreshView(TokenRefreshView):
    """刷新接口：成功后在响应里把新令牌写回 Cookie，保持公网会话连续。"""

    def post(self, request, *args, **kwargs):
        resp = super().post(request, *args, **kwargs)
        if resp.status_code == 200 and isinstance(resp.data, dict) and "access" in resp.data:
            set_auth_cookies(resp, resp.data)
        return resp

from .spa import spa_view

urlpatterns = [
    path("admin/", admin.site.urls),

    # 组织与账号
    path("api/accounts/", include("apps.accounts.urls")),
    # 品牌（白标）公开接口，无需登录
    path("api/branding/", branding_view, name="branding"),
    # 入职培训（文化/制度/知识/考试/入职资料）
    path("api/onboarding/", include("apps.onboarding.urls")),
    # 人事考勤与审批
    path("api/hr/", include("apps.hr.urls")),
    # 工作汇报（日报/周报/月报/复盘）
    path("api/reports/", include("apps.reports.urls")),
    # 电销部
    path("api/sales/", include("apps.sales.urls")),
    # 会计部
    path("api/accounting/", include("apps.accounting.urls")),
    # 运营部
    path("api/ops/", include("apps.ops.urls")),
    # 数据看板（老板驾驶舱）
    path("api/dashboard/", include("apps.dashboard.urls")),
    # 外部能力集成（企业查询/电子营业执照/电子税务局/抖音对标/云账房/视频学习）
    path("api/integrations/", include("apps.integrations.urls")),
    # 会员体系（付费订阅）
    path("api/membership/", include("apps.membership.urls")),
    # 招商板块
    path("api/investment/", include("apps.investment.urls")),
    # 增长中心（纯增量：线索流转 / 3570 / 外勤 / 增值业务部 / 投放统计）
    path("api/growth/", include("apps.growth.urls")),
    # 合同订单名录（电销 / 运营 独立核算，多附件本地上传）
    path("api/contracts/", include("apps.contracts.urls")),
    # 公司通知公告（发布通知 / 发布文件 / 已读回执）
    path("api/notices/", include("apps.notices.urls")),

    path("api/common/", include("apps.common.urls")),  # 操作日志/站内消息/系统配置（2026-10-29）

    # JWT 刷新（公网场景下把新令牌写回 Cookie，保持会话连续）
    path("api/token/refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),

    # 上传附件下载（合同扫描件等）：必须排在 SPA 兜底之前，且 DEBUG 与否均可用
    re_path(r"^media/(?P<path>.*)$", media_serve, {"document_root": settings.MEDIA_ROOT}),

    # 单端口 SPA 托管：非 /api、/admin、/static、/media 的路径统一交给前端路由
    re_path(r"^(?P<path>.*)$", spa_view, name="spa"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
