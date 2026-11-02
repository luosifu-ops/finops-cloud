
# ---------- 2026-10-29 全局能力：操作日志 / 站内通知 / 配置读取 ----------
from apps.common.models import OperationLog, InboxMessage, SystemConfig


def client_ip(request):
    try:
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        return (xff.split(",")[0].strip() or request.META.get("REMOTE_ADDR")) or None
    except Exception:
        return None


def log_action(request, action, module="", obj=None, object_type="", object_id="", detail="", object_repr="", repr_max=120):
    """统一操作日志入口。任何业务动作（增删改/导入导出/审批/分配）都应调用。
    用法: log_action(request, "UPDATE", module="销售线索", obj=lead, detail="阶段 NEW->FOLLOWING")"""
    try:
        u = getattr(request, "user", None)
        oid = object_id or (str(getattr(obj, "id", "")) if obj else "")
        otype = object_type or (obj.__class__.__name__ if obj else "")
        repr_ = ""
        if obj is not None:
            repr_ = str(obj)[:repr_max]
        elif object_repr:
            repr_ = str(object_repr)[:repr_max]
        OperationLog.objects.create(
            user=u if (u and getattr(u, "is_authenticated", False)) else None,
            user_name=(u.display_name if (u and getattr(u, "is_authenticated", False)) else "系统"),
            action=action, module=module, object_type=otype, object_id=oid,
            object_repr=repr_, detail=str(detail)[:2000],
            ip=client_ip(request) if request else None,
        )
    except Exception:
        pass  # 日志失败不影响主业务


def notify_user(recipient, title, body="", category="APPROVAL", link=""):
    """站内消息：审批通过/驳回、任务指派等场景调用"""
    try:
        if not recipient:
            return
        InboxMessage.objects.create(recipient=recipient, title=title[:200], body=body[:2000],
                                    category=category, link=link[:200])
    except Exception:
        pass
