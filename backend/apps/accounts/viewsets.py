import json
import random
import re
import secrets
import urllib.parse
import urllib.request
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, status, permissions, serializers
from rest_framework.decorators import action, api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from config.jwt_auth import set_auth_cookies
from django.contrib.auth import authenticate
from django.db.models import Q
from .models import User, Department, Team, Position, CompanyProfile, PhoneVerifyCode
from .serializers import (
    DepartmentSerializer, TeamSerializer, PositionSerializer,
    UserListSerializer, UserDetailSerializer, UserCreateSerializer,
    CompanyProfileSerializer,
)


def _wechat_get_json(url):
    """调用微信接口并解析 JSON（使用标准库，避免引入额外依赖）"""
    req = urllib.request.Request(url, headers={"User-Agent": "finops-cloud/1.0"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _bind_wechat_identity(user, openid="", unionid="", nickname="", avatar=""):
    """把微信身份写入用户并保存"""
    if openid:
        user.wx_web_openid = openid
    if unionid:
        user.wx_unionid = unionid
    if nickname:
        user.wx_nickname = nickname
    if avatar:
        user.wx_avatar = avatar
    update_fields = [f for f, v in (
        ("wx_web_openid", openid), ("wx_unionid", unionid),
        ("wx_nickname", nickname), ("wx_avatar", avatar),
    ) if v]
    if update_fields:
        user.save(update_fields=update_fields)


def build_token(user):
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def login_view(request):
    """账号密码登录（网站端）"""
    username = request.data.get("username")
    password = request.data.get("password")
    if not username or not password:
        return Response({"code": 1, "msg": "请输入账号和密码"}, status=status.HTTP_400_BAD_REQUEST)
    user = authenticate(username=username, password=password)
    if not user:
        return Response({"code": 1, "msg": "账号或密码错误"}, status=status.HTTP_400_BAD_REQUEST)
    if user.status == "RESIGNED":
        return Response({"code": 1, "msg": "账号已离职停用"}, status=status.HTTP_403_FORBIDDEN)
    token_data = build_token(user)
    resp = Response({"code": 0, "msg": "ok", "data": {
        **token_data,
        "user": UserDetailSerializer(user).data,
    }})
    return set_auth_cookies(resp, token_data)


@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def wx_login_view(request):
    """微信小程序登录：前端 wx.login 拿 code，后端换 openid 后绑定。
    未绑定时返回 need_bind=True，前端引导到绑定页面。
    """
    code = request.data.get("code")
    username = request.data.get("username")
    password = request.data.get("password")
    openid = request.data.get("openid")  # 生产环境应由 code 换取，此处留接口位

    if username and password:
        user = authenticate(username=username, password=password)
        if not user:
            return Response({"code": 1, "msg": "账号或密码错误"})
        if openid:
            user.openid = openid
            user.save(update_fields=["openid"])
        token_data = build_token(user)
        resp = Response({"code": 0, "data": {**token_data, "user": UserDetailSerializer(user).data}})
        return set_auth_cookies(resp, token_data)

    if openid:
        user = User.objects.filter(openid=openid).first()
        if user:
            token_data = build_token(user)
        resp = Response({"code": 0, "data": {**token_data, "user": UserDetailSerializer(user).data}})
        return set_auth_cookies(resp, token_data)
        return Response({"code": 2, "msg": "未绑定账号，请用账号密码登录一次", "data": {"openid": openid}})

    return Response({"code": 1, "msg": "缺少登录参数"})


@api_view(["GET"])
def me_view(request):
    """当前登录用户"""
    return Response({"code": 0, "data": UserDetailSerializer(request.user).data})


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def company_profile_view(request):
    """公司简介与联系方式（单例）。
    GET 返回第一条（不存在则返回空对象）；
    POST 更新/创建（仅老板/人事可写）。
    """
    if request.method == "POST":
        user = request.user
        if not (user.is_superuser or user.role in ("BOSS", "HR")):
            return Response({"code": 1, "msg": "仅老板/人事可编辑公司信息"},
                            status=status.HTTP_403_FORBIDDEN)
        obj = CompanyProfile.objects.filter(is_deleted=False).first()
        if not obj:
            obj = CompanyProfile.objects.create(**request.data)
        else:
            for k, v in request.data.items():
                if k in ("id", "created_at", "updated_at", "is_deleted", "deleted_at", "created_by"):
                    continue
                setattr(obj, k, v)
            obj.save()
        return Response({"code": 0, "msg": "ok", "data": CompanyProfileSerializer(obj).data})

    obj = CompanyProfile.objects.filter(is_deleted=False).first()
    data = CompanyProfileSerializer(obj).data if obj else {}
    return Response({"code": 0, "data": data})


@api_view(["POST"])
def change_password_view(request):
    user = request.user
    old = request.data.get("old_password")
    new = request.data.get("new_password")
    if not user.check_password(old):
        return Response({"code": 1, "msg": "原密码错误"})
    user.set_password(new)
    user.save()
    return Response({"code": 0, "msg": "密码已修改"})


class IsHrManager(permissions.BasePermission):
    """人事板块管理权限：老板 / 管理层 / 人事管理员（含超管）"""
    def has_permission(self, request, view):
        u = request.user
        if not u or not u.is_authenticated:
            return False
        if u.is_superuser:
            return True
        return getattr(u, "role", None) in ("BOSS", "MANAGER", "HR")


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.filter(is_deleted=False)
    serializer_class = DepartmentSerializer
    search_fields = ["name", "code"]
    filterset_fields = ["code"]


class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.filter(is_deleted=False)
    serializer_class = TeamSerializer
    filterset_fields = ["department"]


class PositionViewSet(viewsets.ModelViewSet):
    queryset = Position.objects.filter(is_deleted=False)
    serializer_class = PositionSerializer
    filterset_fields = ["department"]


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("department", "id")
    filterset_fields = ["department", "team", "role", "status"]
    search_fields = ["username", "first_name", "last_name", "phone", "employee_no"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return UserCreateSerializer
        if self.action == "retrieve":
            return UserDetailSerializer
        return UserListSerializer

    def get_queryset(self):
        qs = super().get_queryset().filter(is_active=True)
        user = self.request.user
        dept_id = self.request.query_params.get("department_id")
        if dept_id:
            qs = qs.filter(department_id=dept_id)
        kw = self.request.query_params.get("keyword")
        if kw:
            qs = qs.filter(Q(username__icontains=kw) | Q(first_name__icontains=kw)
                           | Q(last_name__icontains=kw) | Q(phone__icontains=kw))
        if user.is_superuser or user.role in ("BOSS", "HR"):
            return qs
        if user.role == "MANAGER" and user.department_id:
            return qs.filter(department_id=user.department_id)
        if user.role == "LEADER" and user.team_id:
            return qs.filter(team_id=user.team_id)
        return qs.filter(id=user.id)

    @action(detail=False, methods=["get"])
    def teammates(self, request):
        """同部门同事（用于下拉选择）"""
        user = request.user
        qs = self.get_queryset()
        if user.department_id:
            qs = qs.filter(department_id=user.department_id)
        return Response({"code": 0, "data": UserListSerializer(qs, many=True).data})


# ---------------- 微信扫码登录（网站应用 OAuth2）----------------

@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def wx_scan_url_view(request):
    """前端获取微信扫码登录授权地址。
    已配置 WX_OPEN_APPID 时返回真实二维码地址；否则返回 mock 模式标记。
    """
    if not settings.WX_OPEN_APPID:
        scene = secrets.token_hex(8)
        cache.set(f"wxscan:{scene}", {"status": "WAITING"}, 300)
        return Response({"code": 0, "msg": "ok", "data": {
            "mock": settings.WX_SCAN_MOCK,
            "url": None,
            "scene": scene,
            "expire_seconds": 300,
            "tip": "未配置微信开放平台网站应用凭证（WX_OPEN_APPID），当前为模拟扫码模式；"
                   "生产环境请在环境变量中配置 AppID/Secret 并关闭模拟模式。",
        }})
    state = secrets.token_hex(8)
    params = {
        "appid": settings.WX_OPEN_APPID,
        "redirect_uri": settings.WX_OPEN_REDIRECT_URI,
        "response_type": "code",
        "scope": "snsapi_login",
        "state": state,
    }
    url = ("https://open.weixin.qq.com/connect/qrconnect?"
           + urllib.parse.urlencode(params) + "#wechat_redirect")
    cache.set(f"wxscan:{state}", {"status": "WAITING"}, 300)
    return Response({"code": 0, "msg": "ok", "data": {
        "mock": False, "url": url, "state": state, "scene": state, "expire_seconds": 300}})


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def wx_scan_callback_view(request):
    """微信扫码后回跳：用 code 换取 openid/unionid，命中已绑定账号则直接登录，
    否则返回 need_bind 让前端引导绑定。
    """
    code = request.GET.get("code")
    if not code:
        return Response({"code": 1, "msg": "缺少 code 参数"}, status=status.HTTP_400_BAD_REQUEST)
    if not settings.WX_OPEN_APPID:
        return Response({"code": 1, "msg": "未配置微信网站应用凭证，无法完成真实扫码登录"},
                        status=status.HTTP_400_BAD_REQUEST)
    token_url = ("https://api.weixin.qq.com/sns/oauth2/access_token?"
                 + urllib.parse.urlencode({
                     "appid": settings.WX_OPEN_APPID,
                     "secret": settings.WX_OPEN_SECRET,
                     "code": code,
                     "grant_type": "authorization_code",
                 }))
    try:
        tk = _wechat_get_json(token_url)
    except Exception as exc:  # noqa
        return Response({"code": 1, "msg": f"换取微信凭证失败：{exc}"}, status=status.HTTP_400_BAD_REQUEST)
    if "errcode" in tk:
        return Response({"code": 1, "msg": f"微信返回错误：{tk.get('errmsg')}"},
                        status=status.HTTP_400_BAD_REQUEST)
    openid = tk.get("openid", "")
    unionid = tk.get("unionid", "")
    nickname = ""
    avatar = ""
    try:
        ui = _wechat_get_json("https://api.weixin.qq.com/sns/userinfo?"
                              + urllib.parse.urlencode({"access_token": tk["access_token"], "openid": openid}))
        nickname = ui.get("nickname", "")
        avatar = ui.get("headimgurl", "")
    except Exception:  # noqa
        pass
    user = None
    if unionid:
        user = User.objects.filter(wx_unionid=unionid).first()
    if not user and openid:
        user = User.objects.filter(wx_web_openid=openid).first()
    if user:
        _bind_wechat_identity(user, openid, unionid, nickname, avatar)
        payload = {**build_token(user), "user": UserDetailSerializer(user).data}
        state = request.GET.get("state")
        if state:
            cache.set(f"wxscan:{state}", {"status": "SUCCESS", **payload}, 300)
        resp = Response({"code": 0, "data": payload})
        return set_auth_cookies(resp, payload)
    return Response({"code": 2, "msg": "该微信尚未绑定员工账号，请用账号密码绑定一次", "data": {
        "openid": openid, "unionid": unionid, "nickname": nickname, "avatar": avatar}})


@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def wx_scan_mock_view(request):
    """开发/演示用：模拟一次成功的微信扫码登录（默认登录 admin 演示账号）。
    生产环境务必将 WX_SCAN_MOCK 设为 False 关闭此接口。
    """
    if not settings.WX_SCAN_MOCK:
        return Response({"code": 1, "msg": "模拟扫码模式已关闭"}, status=status.HTTP_403_FORBIDDEN)
    username = request.data.get("username") or "admin"
    scene = request.data.get("scene") or ""
    user = User.objects.filter(username=username).first()
    if not user:
        return Response({"code": 1, "msg": f"模拟账号 {username} 不存在"}, status=status.HTTP_404_NOT_FOUND)
    _bind_wechat_identity(user, nickname="模拟微信用户")
    payload = {**build_token(user), "user": UserDetailSerializer(user).data, "mock": True}
    if scene:
        cache.set(f"wxscan:{scene}", {"status": "SUCCESS", **payload}, 300)
    resp = Response({"code": 0, "msg": "ok", "data": payload})
    return set_auth_cookies(resp, payload)


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def wx_scan_status_view(request):
    """前端轮询扫码结果：WAITING / SUCCESS / EXPIRED"""
    scene = request.GET.get("scene") or ""
    data = cache.get(f"wxscan:{scene}")
    if not data:
        return Response({"code": 0, "msg": "ok", "data": {"status": "EXPIRED"}})
    if data.get("status") == "SUCCESS":
        return Response({"code": 0, "msg": "ok", "data": data})
    return Response({"code": 0, "msg": "ok", "data": {"status": "WAITING"}})


# ---------------- 手机号验证码登录 ----------------

SMS_CODE_EXPIRE = 300      # 验证码 5 分钟有效
SMS_RESEND_INTERVAL = 60   # 同一手机号 60 秒内不能重复发送


def _valid_phone(phone):
    return bool(re.fullmatch(r"1[3-9]\d{9}", phone or ""))


@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def sms_send_view(request):
    """发送登录验证码。

    未配置短信网关（SMS_API_KEY）时走演示模式：验证码随响应返回（debug_code），
    生产环境配置网关后此处对接真实短信服务，不再回传验证码。
    """
    phone = (request.data.get("phone") or "").strip()
    scene = request.data.get("scene") or "LOGIN"
    if not _valid_phone(phone):
        return Response({"code": 1, "msg": "请输入正确的 11 位手机号"},
                        status=status.HTTP_400_BAD_REQUEST)

    last = PhoneVerifyCode.objects.filter(phone=phone, scene=scene).order_by("-created_at").first()
    if last and (timezone.now() - last.created_at).total_seconds() < SMS_RESEND_INTERVAL:
        wait = int(SMS_RESEND_INTERVAL - (timezone.now() - last.created_at).total_seconds())
        return Response({"code": 1, "msg": f"发送过于频繁，请 {wait} 秒后再试"},
                        status=status.HTTP_429_TOO_MANY_REQUESTS)

    code = "".join(random.choice("0123456789") for _ in range(6))
    ip = request.META.get("REMOTE_ADDR", "")
    PhoneVerifyCode.objects.create(
        phone=phone, code=code, scene=scene, ip=ip,
        expire_at=timezone.now() + timedelta(seconds=SMS_CODE_EXPIRE),
    )
    demo_mode = not bool(getattr(settings, "SMS_API_KEY", ""))
    data = {
        "phone": phone,
        "expire_seconds": SMS_CODE_EXPIRE,
        "resend_interval": SMS_RESEND_INTERVAL,
        "demo": demo_mode,
    }
    if demo_mode:
        data["debug_code"] = code  # 演示环境直接回传，便于自测
        data["tip"] = "当前未配置短信网关（SMS_API_KEY），验证码已直接返回用于演示。"
    else:
        # TODO: 对接真实短信服务商（阿里云/腾讯云），失败需返回错误
        pass
    return Response({"code": 0, "msg": "验证码已发送", "data": data})


@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def sms_login_view(request):
    """手机号 + 验证码登录。手机号未注册时返回 code=2，引导用账号密码绑定。"""
    phone = (request.data.get("phone") or "").strip()
    code = (request.data.get("code") or "").strip()
    if not _valid_phone(phone):
        return Response({"code": 1, "msg": "请输入正确的 11 位手机号"},
                        status=status.HTTP_400_BAD_REQUEST)
    if not re.fullmatch(r"\d{6}", code):
        return Response({"code": 1, "msg": "验证码为 6 位数字"},
                        status=status.HTTP_400_BAD_REQUEST)

    record = PhoneVerifyCode.objects.filter(
        phone=phone, code=code, scene="LOGIN", used=False
    ).order_by("-created_at").first()
    if not record:
        return Response({"code": 1, "msg": "验证码错误或已失效"},
                        status=status.HTTP_400_BAD_REQUEST)
    if record.expire_at < timezone.now():
        return Response({"code": 1, "msg": "验证码已过期，请重新获取"},
                        status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.filter(phone=phone).first()
    if not user:
        return Response({"code": 2, "msg": "该手机号未绑定员工账号，请先用账号密码登录并在个人中心绑定手机号",
                         "data": {"phone": phone}})
    if user.status == "RESIGNED" or not user.is_active:
        return Response({"code": 1, "msg": "账号已停用"}, status=status.HTTP_403_FORBIDDEN)

    record.used = True
    record.save(update_fields=["used"])
    token_data = build_token(user)
    resp = Response({"code": 0, "msg": "ok", "data": {
        **token_data, "user": UserDetailSerializer(user).data}})
    return set_auth_cookies(resp, token_data)


@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def wx_bind_view(request):
    """need_bind 流程：用账号密码把微信身份绑定到员工账号并登录。"""
    openid = request.data.get("openid", "")
    unionid = request.data.get("unionid", "")
    username = request.data.get("username")
    password = request.data.get("password")
    if not username or not password:
        return Response({"code": 1, "msg": "请输入账号和密码完成绑定"}, status=status.HTTP_400_BAD_REQUEST)
    user = authenticate(username=username, password=password)
    if not user:
        return Response({"code": 1, "msg": "账号或密码错误"}, status=status.HTTP_400_BAD_REQUEST)
    _bind_wechat_identity(user, openid, unionid)
    return Response({"code": 0, "msg": "ok", "data": {
        **build_token(user), "user": UserDetailSerializer(user).data}})


# ============================================================================
# 钉钉式组织架构 · 部门制度 + 入职申请流（2026-09-12 增量，纯新增）
# ============================================================================
from .models import DeptRule, EntryApplication  # noqa: E402


class DeptRuleSerializer(serializers.ModelSerializer):
    rule_type_label = serializers.CharField(source="get_rule_type_display", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    position_name = serializers.CharField(source="position.name", read_only=True, default="")

    class Meta:
        model = DeptRule
        fields = ["id", "department", "department_name", "position", "position_name",
                  "rule_type", "rule_type_label", "title", "content", "created_at"]
        read_only_fields = ["id", "created_at"]


class EntryApplicationSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    department_name = serializers.CharField(source="proposed_department.name", read_only=True, default="")
    position_name = serializers.CharField(source="proposed_position.name", read_only=True, default="")
    reviewed_by_name = serializers.SerializerMethodField()
    resume_url = serializers.SerializerMethodField()

    class Meta:
        model = EntryApplication
        fields = ["id", "applicant_name", "phone", "id_card_no",
                  "proposed_department", "department_name",
                  "proposed_position", "position_name",
                  "expected_salary", "resume", "resume_url",
                  "status", "status_label", "reviewed_by", "reviewed_by_name",
                  "reviewed_at", "reject_reason", "remark", "created_at"]
        read_only_fields = ["id", "status", "status_label", "reviewed_by",
                            "reviewed_by_name", "reviewed_at", "resume_url", "created_at"]

    def get_reviewed_by_name(self, obj):
        if not obj.reviewed_by:
            return ""
        return getattr(obj.reviewed_by, "display_name", None) or obj.reviewed_by.username

    def get_resume_url(self, obj):
        return obj.resume.url if obj.resume else ""


class DeptRuleViewSet(viewsets.ModelViewSet):
    """部门 / 岗位独立制度（老板 / 管理层 / 人事管理员可增删改查）"""
    queryset = DeptRule.objects.filter(is_deleted=False).select_related("department", "position")
    serializer_class = DeptRuleSerializer
    permission_classes = [IsHrManager]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("department"):
            qs = qs.filter(department_id=self.request.query_params["department"])
        if self.request.query_params.get("rule_type"):
            qs = qs.filter(rule_type=self.request.query_params["rule_type"])
        return qs.order_by("department", "rule_type")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save()


class EntryApplicationViewSet(viewsets.ModelViewSet):
    """入职申请：员工提交 → 人事审核 → 自动归类部门岗位（继承该部门制度）"""
    queryset = EntryApplication.objects.filter(is_deleted=False).select_related(
        "proposed_department", "proposed_position", "reviewed_by")
    serializer_class = EntryApplicationSerializer
    ordering_fields = ["created_at", "expected_salary"]

    def get_queryset(self):
        qs = super().get_queryset()
        u = self.request.user
        # 人事管理员看全部；普通员工只看自己提交的
        if getattr(u, "role", None) in ("BOSS", "MANAGER", "HR") or u.is_superuser:
            pass
        else:
            qs = qs.filter(created_by=u)
        if self.request.query_params.get("status"):
            qs = qs.filter(status=self.request.query_params["status"])
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"], permission_classes=[IsHrManager])
    def approve(self, request, pk=None):
        """人事审核通过 → 创建员工账号并归入对应部门/岗位（自动继承该部门制度）"""
        from django.contrib.auth.hashers import make_password
        app = self.get_object()
        if app.status != "PENDING":
            return Response({"detail": "该申请已处理"}, status=status.HTTP_400_BAD_REQUEST)
        dept = app.proposed_department
        pos = app.proposed_position
        base = (app.phone or app.applicant_name).replace(" ", "")[:20]
        username = base
        i = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}{i}"
            i += 1
        user = User.objects.create(
            username=username,
            first_name=app.applicant_name,
            phone=app.phone or None,
            id_card_no=app.id_card_no or "",
            department=dept,
            position=pos,
            role="EMPLOYEE",
            status="PROBATION",
            password=make_password("finops123456"),
        )
        app.status = "APPROVED"
        app.reviewed_by = request.user
        app.reviewed_at = timezone.now()
        app.save(update_fields=["status", "reviewed_by", "reviewed_at"])
        return Response({"detail": "已通过并创建员工账号", "user_id": user.id, "username": username})

    @action(detail=True, methods=["post"], permission_classes=[IsHrManager])
    def reject(self, request, pk=None):
        """拒绝入职申请"""
        app = self.get_object()
        app.status = "REJECTED"
        app.reviewed_by = request.user
        app.reviewed_at = timezone.now()
        app.reject_reason = request.data.get("reject_reason") or ""
        app.save(update_fields=["status", "reviewed_by", "reviewed_at", "reject_reason"])
        return Response({"detail": "已拒绝"})
