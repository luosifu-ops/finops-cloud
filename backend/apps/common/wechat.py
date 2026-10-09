"""微信小程序能力：code2session（换真实 openid）+ 订阅消息推送（2026-10-02 增量，纯新增）

设计原则（与项目既有外部集成完全一致：WECHAT_PAY / LLM / 企查查）：
- 凭证全部走环境变量，未配置时**静默降级返回空/False**，绝不影响主流程；
- 只有 ENABLED=True 且 APPID/SECRET 齐全时才真正向微信发起请求。

关于认证：
- **一次性订阅消息不需要微信认证**，企业/个人主体小程序均可使用；
- 只有「长期订阅消息」才要求行业资质 + 认证。故本模块在未认证时也能工作。

凭证获取：mp.weixin.qq.com → 开发 → 开发管理 → 开发设置（AppID / AppSecret）
模板获取：mp.weixin.qq.com → 订阅消息 → 我的模板 → 选用后复制「模板ID」
"""
import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# access_token 进程内缓存（有效期 7200s，提前 300s 刷新，避免每次都请求）
_TOKEN = {"value": "", "expire_at": 0}

# 订阅消息字段长度限制（微信官方：thing≤20 字符，phrase≤5 字符）
MAX_THING = 20
MAX_PHRASE = 5


def conf():
    return getattr(settings, "WECHAT_MINI", None) or {}


def enabled():
    c = conf()
    return bool(c.get("ENABLED")) and bool(c.get("APPID")) and bool(c.get("SECRET"))


def _cut(s, n):
    s = "" if s is None else str(s)
    return s[:n]


def code2session(code):
    """wx.login 拿到的 code 换取 openid（真实实现）。

    返回 dict（含 openid / session_key / unionid）或 None（未配置 / 失败）。
    未配置凭证时返回 None，前端保持原有「直传 openid」兜底逻辑。
    """
    if not code or not enabled():
        return None
    c = conf()
    try:
        r = requests.get(
            "https://api.weixin.qq.com/sns/jscode2session",
            params={
                "appid": c["APPID"],
                "secret": c["SECRET"],
                "js_code": code,
                "grant_type": "authorization_code",
            },
            timeout=8,
        )
        data = r.json() if r.content else {}
        if data.get("openid"):
            return data
        logger.warning("[wx] code2session 失败：%s", data)
    except Exception as e:  # 网络/解析异常一律降级，不阻断登录
        logger.warning("[wx] code2session 异常：%s", e)
    return None


def get_access_token():
    """获取并缓存 access_token（未配置返回空串）。"""
    if not enabled():
        return ""
    now = time.time()
    if _TOKEN["value"] and _TOKEN["expire_at"] > now + 300:
        return _TOKEN["value"]
    c = conf()
    try:
        r = requests.get(
            "https://api.weixin.qq.com/cgi-bin/token",
            params={
                "grant_type": "client_credential",
                "appid": c["APPID"],
                "secret": c["SECRET"],
            },
            timeout=8,
        )
        data = r.json() if r.content else {}
        token = data.get("access_token")
        if token:
            _TOKEN["value"] = token
            _TOKEN["expire_at"] = now + int(data.get("expires_in", 7200))
            return token
        logger.warning("[wx] access_token 获取失败：%s", data)
    except Exception as e:
        logger.warning("[wx] access_token 异常：%s", e)
    return ""


def send_subscribe_message(openid, template_key, data, page=""):
    """发送一次性订阅消息。

    :param openid: 接收人 openid
    :param template_key: settings.WECHAT_MINI["TEMPLATES"] 中的键
    :param data: 形如 {"thing1": {"value": "..."}}
    :param page: 点击消息跳转的小程序页面（如 pages/hr/leave）
    """
    if not openid or not enabled():
        return False
    tmpl_id = (conf().get("TEMPLATES") or {}).get(template_key)
    if not tmpl_id:
        return False
    token = get_access_token()
    if not token:
        return False
    payload = {
        "touser": openid,
        "template_id": tmpl_id,
        "page": page or "",
        "data": data,
        "miniprogram_state": conf().get("STATE", "formal"),
        "lang": "zh_CN",
    }
    try:
        r = requests.post(
            "https://api.weixin.qq.com/cgi-bin/message/subscribe/send",
            params={"access_token": token},
            json=payload,
            timeout=8,
        )
        res = r.json() if r.content else {}
        if res.get("errcode") == 0:
            return True
        logger.warning("[wx] 订阅消息发送失败 key=%s resp=%s", template_key, res)
    except Exception as e:
        logger.warning("[wx] 订阅消息异常：%s", e)
    return False


def push_approval_result(user, biz_name, approved, remark="", page=""):
    """审批结果推送（请假 / 报销 / 通用）。

    模板字段约定（在 mp 后台选用模板后，按实际字段名调整本函数的 data 键）：
        thing1  审批事项
        phrase2 审批结果
        time3   审批时间
        thing4  审批意见
    """
    openid = getattr(user, "openid", "") if user else ""
    if not openid:
        return False
    from django.utils import timezone
    now = timezone.localtime().strftime("%Y-%m-%d %H:%M")
    data = {
        "thing1": {"value": _cut(biz_name, MAX_THING)},
        "phrase2": {"value": _cut("已通过" if approved else "已驳回", MAX_PHRASE)},
        "time3": {"value": now},
        "thing4": {"value": _cut(remark or "无", MAX_THING)},
    }
    return send_subscribe_message(openid, "APPROVAL_RESULT", data, page)
