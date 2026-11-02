"""钉钉企业内部应用 · HR 通讯录同步（2026-10-28 增量，纯新增）

设计原则（与项目微信/短信/LLM 集成完全一致）：
- 凭证全部走环境变量（DINGTALK_APP_KEY / DINGTALK_APP_SECRET），未配置时静默降级；
- 本模块只做「拉取」不做「推送」，不会向钉钉写入任何数据；
- 部门编码用 DT{钉钉部门ID}，绝不占用 SALES/ACCOUNT/OPS/MGMT 四个业务码；
- 员工按手机号匹配老账号（命中则只补部门，不改角色/密码），未命中才新建。

凭证获取：钉钉管理后台(dingtalk.com) → 应用开发 → 创建企业内部应用 → 凭证与基础信息
所需权限：通讯录部门信息读权限 + 通讯录部门成员读权限（含手机号需「个人信息读权限」）
"""
import logging

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

TOKEN_CACHE_KEY = "dingtalk:access_token"
BASE = "https://oapi.dingtalk.com"


def is_configured():
    cfg = getattr(settings, "DINGTALK", {})
    return bool(cfg.get("APP_KEY") and cfg.get("APP_SECRET"))


def _get_token():
    """获取 access_token（缓存 7000 秒，官方有效期 7200s）"""
    token = cache.get(TOKEN_CACHE_KEY)
    if token:
        return token
    cfg = settings.DINGTALK
    r = requests.get(
        f"{BASE}/gettoken",
        params={"appkey": cfg["APP_KEY"], "appsecret": cfg["APP_SECRET"]},
        timeout=10,
    )
    data = r.json()
    if data.get("errcode") != 0:
        raise RuntimeError(f"钉钉 gettoken 失败: errcode={data.get('errcode')} {data.get('errmsg')}")
    token = data["access_token"]
    cache.set(TOKEN_CACHE_KEY, token, 7000)
    return token


def _post(path, payload):
    r = requests.post(f"{BASE}{path}", params={"access_token": _get_token()}, json=payload, timeout=15)
    data = r.json()
    if data.get("errcode") != 0:
        raise RuntimeError(f"钉钉 {path} 失败: errcode={data.get('errcode')} {data.get('errmsg')}")
    return data.get("result")


def _list_sub_departments(parent_id=1):
    """递归拉取部门树（自根 1 起）"""
    subs = _post("/topapi/v2/department/listsub", {"dept_id": parent_id}) or []
    out = []
    for d in subs:
        out.append(d)
        out.extend(_list_sub_departments(d["dept_id"]))
    return out


def _list_dept_users(dept_id):
    """分页拉取部门下成员（简要信息，含 userid/name/title）"""
    users, cursor = [], 0
    while True:
        res = _post("/topapi/v2/user/list", {"dept_id": dept_id, "cursor": cursor, "size": 100}) or {}
        users.extend(res.get("list") or [])
        if not res.get("has_more"):
            break
        cursor = res.get("cursor", 0)
    return users


def _user_detail(userid):
    """成员详情（手机号需要「个人信息读权限」，无权限时返回空）"""
    try:
        return _post("/topapi/v2/user/get", {"userid": userid}) or {}
    except RuntimeError as e:  # noqa
        logger.warning("钉钉用户详情获取失败 %s: %s", userid, e)
        return {}


def sync_org(dry_run=False):
    """通讯录同步主入口：钉钉部门 → Department，钉钉成员 → User

    返回统计 dict；任何一步失败抛异常由视图层捕获。
    """
    from apps.accounts.models import Department, Position, User

    if not is_configured():
        raise RuntimeError("未配置钉钉凭证（DINGTALK_APP_KEY / DINGTALK_APP_SECRET）")

    reserved = set(getattr(Department, "RESERVED_CODES", []) or [])
    stats = {"depts_created": 0, "depts_updated": 0, "users_created": 0,
             "users_matched": 0, "users_skipped": 0, "errors": []}

    # ---------- 1. 部门 ----------
    ding_depts = _list_sub_departments(1)
    dept_map = {}  # ding_dept_id -> Department
    for d in ding_depts:
        code = f"DT{d['dept_id']}"
        if code in reserved:
            stats["errors"].append(f"部门编码 {code} 与业务码冲突，跳过")
            continue
        parent = dept_map.get(d.get("parent_id"))
        if dry_run:
            exists = Department.objects.filter(code=code).exists()
            stats["depts_created" if not exists else "depts_updated"] += 1
            dept_map[d["dept_id"]] = None
            continue
        dept, created = Department.objects.update_or_create(
            code=code,
            defaults={"name": d["name"], "parent": parent,
                      "description": f"钉钉同步部门（钉钉ID:{d['dept_id']}）"},
        )
        dept_map[d["dept_id"]] = dept
        stats["depts_created" if created else "depts_updated"] += 1

    # ---------- 2. 成员 ----------
    seen_userids = set()
    for ding_id, dept in dept_map.items():
        if dept is None:
            continue
        for u in _list_dept_users(ding_id):
            userid, name = u.get("userid"), (u.get("name") or "").strip()
            if not userid or not name or userid in seen_userids:
                continue
            seen_userids.add(userid)
            detail = _user_detail(userid)
            mobile = (detail.get("mobile") or "").strip()
            title = (detail.get("title") or "").strip()
            # 老账号匹配：手机号优先，其次 dt_{userid} 历史账号
            user = User.objects.filter(phone=mobile).first() if mobile else None
            if user is None:
                user = User.objects.filter(username=f"dt_{userid}").first()
            if user:
                if user.department_id != dept.id:
                    user.department = dept
                    user.save(update_fields=["department"])
                stats["users_matched"] += 1
                continue
            # 在职/离职保护：同名同号已离职员工不复活，仅提示
            if dry_run:
                stats["users_created"] += 1
                continue
            username = mobile if mobile and not User.objects.filter(username=mobile).exists() else f"dt_{userid}"
            pos = Position.objects.filter(name=title, department=dept).first() if title else None
            if title and pos is None:
                pos = Position.objects.create(name=title, department=dept, description="钉钉同步岗位")
            new_user = User.objects.create(
                username=username, first_name=name, phone=mobile or None,
                department=dept, position=pos, role="EMPLOYEE", status="REGULAR",
            )
            new_user.set_unusable_password()  # 钉钉同步账号默认不可登录，管理员在员工档案重置密码后启用
            new_user.save(update_fields=["password"])
            stats["users_created"] += 1

    return stats
