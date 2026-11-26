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
    """账号密码登录（网站端）。带防刷限流：同 IP+账号 10 分钟内失败 5 次锁定。"""
    username = request.data.get("username")
    password = request.data.get("password")
    if not username or not password:
        return Response({"code": 1, "msg": "请输入账号和密码"}, status=status.HTTP_400_BAD_REQUEST)
    # —— 防刷限流（全局规则：登录页增强）——
    from django.core.cache import cache
    ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR", "")
    lock_key = f"login_fail:{ip}:{username}"
    fails = cache.get(lock_key, 0)
    if fails >= 5:
        return Response({"code": 1, "msg": "失败次数过多，账号已临时锁定，请 10 分钟后再试或用短信验证码登录"},
                        status=status.HTTP_429_TOO_MANY_REQUESTS)
    user = authenticate(username=username, password=password)
    if not user:
        cache.set(lock_key, fails + 1, 600)
        left = 5 - (fails + 1)
        return Response({"code": 1, "msg": f"账号或密码错误（剩余尝试次数 {left}）"},
                        status=status.HTTP_400_BAD_REQUEST)
    cache.delete(lock_key)
    if user.status == "RESIGNED":
        return Response({"code": 1, "msg": "账号已离职停用"}, status=status.HTTP_403_FORBIDDEN)
    token_data = build_token(user)
    from apps.common.services import log_action
    log_action(request, "LOGIN", module="登录", obj=user)
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
    openid = request.data.get("openid")  # 兜底：前端直传（原逻辑保留）
    # 2026-10-02 增量：配置了小程序凭证时，用 code 向微信换取真实 openid
    if not openid and code:
        from apps.common import wechat
        sess = wechat.code2session(code)
        if sess:
            openid = sess.get("openid")

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
        # 2026-10-31 修复：openid 未绑定任何账号时，原代码引用未定义的 token_data 会 500，
        # 且 need_bind 分支是 return 之后的死代码。现正确返回 need_bind 引导绑定。
        return Response({"code": 2, "msg": "未绑定账号，请用账号密码登录一次", "data": {"openid": openid}})

    # 2026-10-31 修复：无 username/password 且没换到 openid（未配置凭证或 code 失效）时，
    # 旧版返回「缺少登录参数」误导用户。现区分场景给明确引导。
    if code:
        from apps.common import wechat
        if not wechat.enabled():
            return Response({"code": 2, "msg": "微信登录暂未开通，请用账号密码登录", "data": {"reason": "wx_credentials_missing"}})
        return Response({"code": 2, "msg": "微信登录已过期，请重试或用账号密码登录", "data": {"reason": "code_invalid"}})
    return Response({"code": 1, "msg": "缺少登录参数"})


@api_view(["GET", "PATCH"])
def me_view(request):
    """当前登录用户；PATCH 更新个人信息（显示名/手机号/头像）"""
    user = request.user
    if request.method == "PATCH":
        from .models import User as U
        data = request.data
        changed = []
        if "display_name" in data and isinstance(data["display_name"], str) and data["display_name"].strip():
            # display_name 是只读 property（first_name + last_name 拼接），此处拆写底层字段
            name = data["display_name"].strip().replace(" ", "")
            user.first_name = name[0]
            user.last_name = name[1:] if len(name) > 1 else ""
            changed.append("display_name")
        if "phone" in data:
            phone = (data.get("phone") or "").strip()
            if phone and (not re.fullmatch(r"1[3-9]\d{9}", phone)):
                return Response({"code": 1, "msg": "手机号格式不正确"}, status=status.HTTP_400_BAD_REQUEST)
            if phone and U.objects.filter(phone=phone).exclude(id=user.id).exists():
                return Response({"code": 1, "msg": "该手机号已被其他员工绑定"}, status=status.HTTP_400_BAD_REQUEST)
            user.phone = phone or None
            changed.append("phone")
        if "avatar" in request.FILES:
            user.avatar = request.FILES["avatar"]
            changed.append("avatar")
        if changed:
            user.save()
            from apps.common.services import log_action
            log_action(request, "UPDATE", module="个人中心", object_type="User",
                       object_id=user.id, object_repr=user.display_name, detail="更新: " + ",".join(changed))
        return Response({"code": 0, "msg": "已保存", "data": UserDetailSerializer(user).data})
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


class OrgWriteGuardMixin:
    """组织架构隔离墙：增删改仅老板 / 管理层 / 人事（2026-10-28 Boss 指示补部门级隔离墙）。
    查询默认需登录；public_list=True 的视图（部门/岗位）放开只读查询，
    供登录页「申请入职」公开页匿名拉取部门/岗位下拉。
    """
    public_list = False

    def get_permissions(self):
        if self.action in ("list", "retrieve") and self.public_list:
            return [permissions.AllowAny()]
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated()]
        return [IsHrManager()]


class DepartmentViewSet(OrgWriteGuardMixin, viewsets.ModelViewSet):
    queryset = Department.objects.filter(is_deleted=False)
    serializer_class = DepartmentSerializer
    search_fields = ["name", "code"]
    filterset_fields = ["code"]
    public_list = True  # 公开只读：申请入职页需匿名选择意向部门


class TeamViewSet(OrgWriteGuardMixin, viewsets.ModelViewSet):
    queryset = Team.objects.filter(is_deleted=False)
    serializer_class = TeamSerializer
    filterset_fields = ["department"]


class PositionViewSet(OrgWriteGuardMixin, viewsets.ModelViewSet):
    queryset = Position.objects.filter(is_deleted=False)
    serializer_class = PositionSerializer
    filterset_fields = ["department"]
    public_list = True  # 公开只读：申请入职页需匿名选择意向岗位


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("department", "id")
    filterset_fields = ["department", "team", "role", "status"]
    search_fields = ["username", "first_name", "last_name", "phone", "employee_no"]

    def get_permissions(self):
        # 隔离墙（2026-10-28）：新增/删除员工仅老板/人事；改资料限管理层或本人
        if self.action in ("create", "destroy"):
            return [IsHrManager()]
        return [permissions.IsAuthenticated()]

    def perform_destroy(self, instance):
        """删除账号规则（2026-10-29 Boss 指示：员工可以删，老板不能删）：
        1) 禁止删除当前登录账号自己；
        2) 老板(BOSS)/超级管理员账号一律不允许删除，直接提示；如需停用改为离职状态即可；
        3) 员工删除 = 软删除（停用+离职），保留历史数据引用，不物理删除。
        """
        me = self.request.user
        if instance.id == me.id:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("不能删除当前登录的账号自己。")
        if instance.is_superuser or instance.role == "BOSS":
            from rest_framework.exceptions import ValidationError
            raise ValidationError("老板/管理员账号不允许删除。如需停用，请把该员工状态改为「离职」即可。")
        instance.is_active = False
        instance.status = "RESIGNED"
        instance.save(update_fields=["is_active", "status"])

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return UserCreateSerializer
        if self.action == "retrieve":
            return UserDetailSerializer
        return UserListSerializer

    def get_queryset(self):
        qs = super().get_queryset().filter(is_active=True)
        user = self.request.user
        params = self.request.query_params
        dept_id = params.get("department_id")
        if dept_id:
            qs = qs.filter(department_id=dept_id)
        kw = params.get("keyword")
        if kw:
            qs = qs.filter(Q(username__icontains=kw) | Q(first_name__icontains=kw)
                           | Q(last_name__icontains=kw) | Q(phone__icontains=kw)
                           | Q(employee_no__icontains=kw))
        # 角色 / 状态 / 部门筛选（2026-10-29 员工管理专项）
        # 说明：项目未安装 django-filter，DRF 默认只挂了 Search/Ordering 两个后端，
        # 原来的 filterset_fields 实际不生效（传了 ?role= 也没用）。这里显式解析，
        # 保证前端「角色 / 状态 / 部门」下拉筛选真正生效。
        role = params.get("role")
        if role:
            qs = qs.filter(role=role)
        emp_status = params.get("status")
        if emp_status:
            qs = qs.filter(status=emp_status)
        department = params.get("department")
        if department:
            qs = qs.filter(department_id=department)
        if user.is_superuser or user.role in ("BOSS", "HR"):
            return qs
        # 2026-11-03 Boss 指示：拥有「线索分配」权限的人需要选人（归属运营 / 承接人），
        # 否则分配弹窗只能看到自己。仅 when ?for_assign=1 且已授权时放开全员名单。
        if params.get("for_assign") in ("1", "true", "True"):
            from apps.common.permissions import can_assign_leads as _can_assign_leads
            if _can_assign_leads(user):
                return qs
        if user.role == "MANAGER" and user.department_id:
            return qs.filter(department_id=user.department_id)
        if user.role == "LEADER" and user.team_id:
            return qs.filter(team_id=user.team_id)
        return qs.filter(id=user.id)

    @action(detail=False, methods=["post"], url_path="bulk-delete", permission_classes=[IsHrManager])
    def bulk_delete(self, request):
        """批量删除员工（2026-10-30 修复员工管理批量删除按钮不可用）。

        与单条删除规则保持一致（软删除 = 停用 + 置为离职）：
        1) 跳过当前登录账号自己；
        2) 老板(BOSS)/超级管理员账号一律跳过，不删除；
        3) 其余员工置为 is_active=False + RESIGNED，保留历史数据引用，可恢复。
        """
        # 显式权限墙：仅老板/管理层/人事（含超管）。放在动作内校验，
        # 避免 ViewSet 级 get_permissions 覆盖 action 的 permission_classes。
        u = request.user
        if not (u.is_superuser or getattr(u, "role", None) in ("BOSS", "MANAGER", "HR")):
            return Response({"code": 1, "msg": "仅老板/管理层/人事可批量删除员工"},
                            status=status.HTTP_403_FORBIDDEN)
        ids = request.data.get("ids") or []
        if not isinstance(ids, list) or not ids:
            return Response({"code": 1, "msg": "请先勾选要删除的员工"},
                            status=status.HTTP_400_BAD_REQUEST)
        me = request.user
        ok, skip = 0, 0
        for u in User.objects.filter(id__in=ids):
            if u.id == me.id or u.is_superuser or u.role == "BOSS":
                skip += 1
                continue
            u.is_active = False
            u.status = "RESIGNED"
            u.save(update_fields=["is_active", "status"])
            from apps.common.services import log_action
            log_action(request, "BULK_DELETE", module="员工管理", obj=u)
            ok += 1
        msg = f"已删除 {ok} 名员工（停用并置为离职）"
        if skip:
            msg += f"；跳过 {skip} 名（老板/管理员与当前登录账号不可删除）"
        return Response({"code": 0, "msg": msg, "deleted": ok})

    @action(detail=False, methods=["get"])
    def teammates(self, request):
        """同部门同事（用于下拉选择）"""
        user = request.user
        qs = self.get_queryset()
        if user.department_id:
            qs = qs.filter(department_id=user.department_id)
        return Response({"code": 0, "data": UserListSerializer(qs, many=True).data})

    # ---------- 入离职批量导入（2026-10-29 Boss 专项） ----------
    TEMPLATE_HEADERS = ["姓名", "手机号", "部门", "岗位", "角色", "入职日期", "状态", "初始密码"]

    @action(detail=False, methods=["get"], url_path="import-template")
    def import_template(self, request):
        """下载批量导入模板（CSV，UTF-8 BOM，Excel 直接打开不乱码）"""
        import csv
        import io
        from django.http import HttpResponse
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(self.TEMPLATE_HEADERS)
        w.writerow(["张三", "13800001111", "电销部", "销售顾问", "员工", "2026-10-01", "试用期", ""])
        w.writerow(["李四", "13800002222", "会计部", "主办会计", "员工", "2026-10-01", "正式", ""])
        body = "\ufeff" + buf.getvalue()
        resp = HttpResponse(body, content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="employee_import_template.csv"'
        return resp

    @action(detail=False, methods=["post"], url_path="bulk-import", permission_classes=[IsHrManager])
    def bulk_import(self, request):
        """批量导入员工（入/离职一批处理）

        请求体：{"rows": [{name, phone, department_name, position_name, role_name,
                          entry_date, status_name, password}]}
        - 部门/岗位按名称匹配（不存在则报错该行，不静默丢弃）
        - 角色：老板/管理层/主管/人事/员工 → BOSS/MANAGER/LEADER/HR/EMPLOYEE
        - 状态：试用期/正式/离职 → PROBATION/REGULAR/RESIGNED
        - 密码留空则生成 12 位临时密码，仅在返回结果中出现一次
        """
        import secrets
        from django.contrib.auth.hashers import make_password
        rows = request.data.get("rows") or []
        if not rows:
            return Response({"code": 1, "msg": "没有可导入的数据行"}, status=status.HTTP_400_BAD_REQUEST)

        role_map = {"老板": "BOSS", "管理层": "MANAGER", "经理": "MANAGER",
                    "主管": "LEADER", "人事": "HR", "员工": "EMPLOYEE"}
        status_map = {"试用期": "PROBATION", "正式": "REGULAR", "在职": "REGULAR", "离职": "RESIGNED"}
        depts = {d.name: d for d in Department.objects.all()}
        positions = {p.name: p for p in Position.objects.all()}
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"

        ok, fail, results = 0, 0, []
        for idx, r in enumerate(rows, start=2):  # 第 2 行起（第 1 行表头）
            name = (r.get("name") or r.get("姓名") or "").strip()
            phone = (r.get("phone") or r.get("手机号") or "").strip()
            dept_name = (r.get("department_name") or r.get("部门") or "").strip()
            pos_name = (r.get("position_name") or r.get("岗位") or "").strip()
            role_name = (r.get("role_name") or r.get("角色") or "员工").strip()
            entry_date = (r.get("entry_date") or r.get("入职日期") or "").strip()
            status_name = (r.get("status_name") or r.get("状态") or "试用期").strip()
            password = (r.get("password") or r.get("初始密码") or "").strip()

            err = []
            if not name:
                err.append("姓名为空")
            if not phone or not re.fullmatch(r"1[3-9]\d{9}", phone):
                err.append("手机号格式不正确")
            if dept_name and dept_name not in depts:
                err.append(f"部门「{dept_name}」不存在")
            if phone and User.objects.filter(phone=phone).exists():
                err.append("手机号已被现有员工占用")
            if err:
                fail += 1
                results.append({"row": idx, "name": name, "ok": False, "reason": "；".join(err)})
                continue

            one_time = ""
            pwd_hash = None
            if password:
                if len(password) < 8:
                    fail += 1
                    results.append({"row": idx, "name": name, "ok": False, "reason": "初始密码至少 8 位"})
                    continue
                pwd_hash = make_password(password)
            else:
                one_time = "".join(secrets.choice(alphabet) for _ in range(12))
                pwd_hash = make_password(one_time)

            username = phone
            i = 1
            while User.objects.filter(username=username).exists():
                username = f"{phone}_{i}"
                i += 1
            try:
                u = User.objects.create(
                    username=username,
                    first_name=name[0],
                    last_name=name[1:] if len(name) > 1 else "",
                    phone=phone,
                    department=depts.get(dept_name),
                    position=positions.get(pos_name),
                    role=role_map.get(role_name, "EMPLOYEE"),
                    status=status_map.get(status_name, "PROBATION"),
                    password=pwd_hash,
                    is_active=status_map.get(status_name) != "RESIGNED",
                )
                if entry_date:
                    try:
                        from datetime import datetime as _dt
                        u.entry_date = _dt.strptime(entry_date.replace("/", "-"), "%Y-%m-%d").date()
                        u.save(update_fields=["entry_date"])
                    except ValueError:
                        pass
                ok += 1
                results.append({"row": idx, "name": name, "ok": True, "username": username,
                                "one_time_password": one_time})
            except Exception as e:  # 任何建号失败都要定位到行
                fail += 1
                results.append({"row": idx, "name": name, "ok": False, "reason": str(e)[:120]})

        from apps.common.services import log_action
        log_action(request, "IMPORT", module="员工管理",
                   detail=f"批量导入员工：成功 {ok} 条，失败 {fail} 条")
        return Response({"code": 0, "msg": f"导入完成：成功 {ok} 条，失败 {fail} 条",
                         "ok": ok, "fail": fail, "results": results})


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


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def wx_bind_openid_view(request):
    """2026-10-02 增量：把当前已登录账号与小程序 openid 绑定（用于订阅消息推送）。

    纯新增接口，不改动 wx_bind_view 的「账号密码绑定」流程。
    入参：{ "code": "wx.login 拿到的 code" }，或 { "openid": "..." } 兜底直传。

    2026-10-31 修复：此接口在小程序端是登录后静默调用（login.js bindOpenid，
    失败不影响任何功能），但旧版在「未配置小程序凭证 / code 已失效」时返回
    code:1 + msg，被小程序 app.js 全局拦截器 wx.showToast 弹窗骚扰用户。
    现改为：凭证未配置 / code 换取失败一律静默返回 code:0 + bound:false；
    只有真实换到 openid 时才执行绑定。同时并入防重复绑定校验
    （同一微信号已绑定其他账号时不覆盖）。
    """
    from apps.common import wechat

    openid = request.data.get("openid", "")
    code = request.data.get("code", "")
    if not openid and code:
        if not wechat.enabled():
            # 未配置 WX_OPEN_APPID/WX_OPEN_SECRET：静默返回，绝不弹窗、不影响主流程
            return Response({"code": 0, "msg": "ok", "data": {"bound": False, "reason": "wx_credentials_missing"}})
        sess = wechat.code2session(code)
        if sess:
            openid = sess.get("openid", "")
    if not openid:
        # code 无效/过期（wx.login 的 code 5 分钟有效且一次性）：静默返回
        return Response({"code": 0, "msg": "ok", "data": {"bound": False, "reason": "code_invalid_or_expired"}})
    # 防重复绑定：该微信号已绑定其他账号时不抢占
    if User.objects.filter(openid=openid).exclude(id=request.user.id).exists():
        return Response({"code": 0, "msg": "ok", "data": {"bound": False, "reason": "openid_owned_by_other"}})
    user = request.user
    if user.openid != openid:
        user.openid = openid
        user.save(update_fields=["openid"])
    return Response({"code": 0, "msg": "ok", "data": {"openid": openid, "bound": True}})


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

    # password：申请时自设登录密码（只写不读，写入时立即哈希）
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=128,
                                     help_text="员工自设登录密码，审核通过后生效")

    class Meta:
        model = EntryApplication
        fields = ["id", "applicant_name", "phone", "id_card_no", "password",
                  "proposed_department", "department_name",
                  "proposed_position", "position_name",
                  "expected_salary", "resume", "resume_url",
                  "status", "status_label", "reviewed_by", "reviewed_by_name",
                  "reviewed_at", "reject_reason", "remark", "created_at"]
        read_only_fields = ["id", "status", "status_label", "reviewed_by",
                            "reviewed_by_name", "reviewed_at", "resume_url", "created_at"]

    def validate_password(self, value):
        """申请时自设密码校验：8-64 位，不允许留空即使用统一弱口令"""
        if not value:
            return value
        if len(value) < 8 or len(value) > 64:
            raise serializers.ValidationError("登录密码需 8-64 位")
        if value in ("finops123456", "admin123", "12345678", "password"):
            raise serializers.ValidationError("该密码过于常见，请更换")
        return value

    def create(self, validated_data):
        from django.contrib.auth.hashers import make_password
        raw = validated_data.pop("password", "")
        if raw:
            validated_data["password_hash"] = make_password(raw)
        return super().create(validated_data)

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
    """入职申请：员工提交 → 人事审核 → 自动归类部门岗位（继承该部门制度）
    2026-10-28 增量：支持未登录访客在登录页「申请入职」提交（create 放开为 AllowAny）
    """
    queryset = EntryApplication.objects.filter(is_deleted=False).select_related(
        "proposed_department", "proposed_position", "reviewed_by")
    serializer_class = EntryApplicationSerializer
    ordering_fields = ["created_at", "expected_salary"]

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        u = self.request.user
        # 人事管理员看全部；普通员工只看自己提交的
        if getattr(u, "role", None) in ("BOSS", "MANAGER", "HR") or u.is_superuser:
            pass
        elif u and u.is_authenticated:
            qs = qs.filter(created_by=u)
        else:
            qs = qs.none()
        if self.request.query_params.get("status"):
            qs = qs.filter(status=self.request.query_params["status"])
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        u = self.request.user
        serializer.save(created_by=u if (u and u.is_authenticated) else None)

    @action(detail=True, methods=["post"], permission_classes=[IsHrManager])
    def approve(self, request, pk=None):
        """人事审核通过 → 创建员工账号并归入对应部门/岗位（自动继承该部门制度）
        密码策略（2026-10-28 体检）：员工申请时已自设密码 → 直接启用；
        旧数据无自设密码时随机生成 12 位一次性密码并返回给人事，仅此一次展示。
        """
        import secrets
        from django.contrib.auth.hashers import make_password
        app = self.get_object()
        if app.status != "PENDING":
            return Response({"detail": "该申请已处理"}, status=status.HTTP_400_BAD_REQUEST)
        # 2026-10-29 Boss 指示：审核时可指定实际部门/岗位/角色（默认带出员工申请意向）。
        # 员工申请时经常选错部门，若按意向直接归档会导致其登录后菜单功能不全。
        from .models import Position
        dept = None
        dep_id = request.data.get("department")
        if dep_id:
            dept = Department.objects.filter(id=dep_id).first()
        dept = dept or app.proposed_department
        pos = None
        pos_id = request.data.get("position")
        if pos_id:
            pos = Position.objects.filter(id=pos_id).first()
        pos = pos or app.proposed_position
        valid_roles = {r[0] for r in User.ROLE_CHOICES}
        role = request.data.get("role")
        role = role if role in valid_roles else "EMPLOYEE"
        base = (app.phone or app.applicant_name).replace(" ", "")[:20]
        username = base
        i = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}{i}"
            i += 1
        one_time_password = ""
        if app.password_hash:
            initial_password = app.password_hash  # 已是哈希，直接落库
        else:
            # 兼容旧申请：随机一次性密码，返回给人事当面转交
            alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"
            one_time_password = "".join(secrets.choice(alphabet) for _ in range(12))
            initial_password = make_password(one_time_password)
        # 唯一字段冲突预检：避免 IntegrityError 裸 500（2026-10-29 入职审核 500 修复）
        dup = []
        if app.phone and User.objects.filter(phone=app.phone).exists():
            dup.append(f"手机号 {app.phone} 已被其他员工绑定")
        if app.id_card_no and User.objects.filter(id_card_no=app.id_card_no).exists():
            dup.append(f"身份证号已被其他员工绑定")
        if dup:
            return Response({"detail": "；".join(dup) + "，请核对员工档案后再审核"},
                            status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.create(
            username=username,
            first_name=app.applicant_name,
            phone=app.phone or None,
            id_card_no=app.id_card_no or "",
            department=dept,
            position=pos,
            role=role,
            status="PROBATION",
            password=initial_password,
        )
        app.status = "APPROVED"
        app.reviewed_by = request.user
        app.reviewed_at = timezone.now()
        app.save(update_fields=["status", "reviewed_by", "reviewed_at"])
        from apps.common.services import log_action, notify_user
        log_action(request, "APPROVE", module="入职审核", obj=app, detail=f"通过{app.applicant_name}的入职申请并建号({username})")
        if app.created_by and app.created_by_id != request.user.id:
            notify_user(app.created_by, "你的入职申请已通过",
                        f"{app.applicant_name} 的入职申请已审核通过，账号 {username} 已创建。", link="/hr/entry-review")
        data = {"detail": "已通过并创建员工账号", "user_id": user.id, "username": username,
                "password_from": "self" if app.password_hash else "one_time"}
        if one_time_password:
            data["one_time_password"] = one_time_password  # 仅旧数据返回，请人事立即转交
        return Response(data)

    @action(detail=True, methods=["post"], permission_classes=[IsHrManager])
    def reject(self, request, pk=None):
        """拒绝入职申请"""
        app = self.get_object()
        app.status = "REJECTED"
        app.reviewed_by = request.user
        app.reviewed_at = timezone.now()
        app.reject_reason = request.data.get("reject_reason") or ""
        app.save(update_fields=["status", "reviewed_by", "reviewed_at", "reject_reason"])
        from apps.common.services import log_action, notify_user
        log_action(request, "REJECT", module="入职审核", obj=app, detail=f"拒绝原因: {app.reject_reason}")
        if app.created_by and app.created_by_id != request.user.id:
            notify_user(app.created_by, "你的入职申请未通过",
                        f"{app.applicant_name} 的入职申请被驳回。原因：{app.reject_reason or '未填写'}", link="/hr/entry-review")
        return Response({"detail": "已拒绝"})
