from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import viewsets

router = DefaultRouter()
router.register("departments", viewsets.DepartmentViewSet, basename="department")
router.register("teams", viewsets.TeamViewSet, basename="team")
router.register("positions", viewsets.PositionViewSet, basename="position")
router.register("users", viewsets.UserViewSet, basename="user")
router.register("dept-rules", viewsets.DeptRuleViewSet, basename="dept-rule")
router.register("entries", viewsets.EntryApplicationViewSet, basename="entry-application")

urlpatterns = [
    path("auth/login/", viewsets.login_view, name="login"),
    # 手机号验证码登录
    path("auth/sms/send/", viewsets.sms_send_view, name="sms-send"),
    path("auth/sms/login/", viewsets.sms_login_view, name="sms-login"),
    path("auth/wx-login/", viewsets.wx_login_view, name="wx-login"),
    path("auth/wx-scan/url/", viewsets.wx_scan_url_view, name="wx-scan-url"),
    path("auth/wx-scan/callback/", viewsets.wx_scan_callback_view, name="wx-scan-callback"),
    path("auth/wx-scan/mock/", viewsets.wx_scan_mock_view, name="wx-scan-mock"),
    path("auth/wx-scan/status/", viewsets.wx_scan_status_view, name="wx-scan-status"),
    path("auth/wx-bind/", viewsets.wx_bind_view, name="wx-bind"),
    path("auth/me/", viewsets.me_view, name="me"),
    path("auth/change-password/", viewsets.change_password_view, name="change-password"),
    path("company/", viewsets.company_profile_view, name="company-profile"),
    path("", include(router.urls)),
]
