"""全局基础 API：操作日志 / 站内消息 / 系统配置（第三方API密钥可视化维护）"""
from rest_framework import serializers, viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response

from .models import OperationLog, InboxMessage, SystemConfig
from .services import log_action


class OperationLogSerializer(serializers.ModelSerializer):
    action_name = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = OperationLog
        fields = "__all__"


class OperationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """操作日志：老板/人事看全公司，部门主管看本部门，其他人看自己的"""
    serializer_class = OperationLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        u = self.request.user
        qs = OperationLog.objects.all()
        # 2026-10-29 权限专项：主管原来能拉全公司操作日志（跨部门泄露），
        # 现收敛为「老板/人事全量 → 主管本部门 → 其他本人」
        if not (u.is_superuser or u.role in ("BOSS", "HR")):
            if u.role == "MANAGER" and u.department_id:
                qs = qs.filter(user__department_id=u.department_id)
            elif u.role == "LEADER" and u.team_id:
                qs = qs.filter(user__team_id=u.team_id)
            else:
                qs = qs.filter(user=u)
        p = self.request.query_params
        if p.get("start_date"):
            qs = qs.filter(created_at__gte=p["start_date"])
        if p.get("end_date"):
            qs = qs.filter(created_at__lte=p["end_date"] + " 23:59:59" if len(p["end_date"]) <= 10 else p["end_date"])
        if p.get("action"):
            qs = qs.filter(action=p["action"])
        if p.get("module"):
            qs = qs.filter(module__icontains=p["module"])
        if p.get("keyword"):
            qs = qs.filter(user_name__icontains=p["keyword"]) | qs.filter(object_repr__icontains=p["keyword"])
        return qs


class InboxSerializer(serializers.ModelSerializer):
    class Meta:
        model = InboxMessage
        fields = ["id", "title", "body", "category", "link", "is_read", "created_at"]


class InboxViewSet(viewsets.ReadOnlyModelViewSet):
    """站内消息：审批结果通知等。只看自己的"""
    serializer_class = InboxSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return InboxMessage.objects.filter(recipient=self.request.user)

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        return Response({"count": self.get_queryset().filter(is_read=False).count()})

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        msg = self.get_queryset().filter(id=pk).first()
        if msg:
            msg.is_read = True
            msg.save(update_fields=["is_read"])
        return Response({"code": 0})

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        n = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({"code": 0, "msg": f"已读 {n} 条"})


SECRET_KEYS = [
    {"key": "QICHACHA_API_KEY", "name": "企查查 API Key", "remark": "企业查询（工商信息）", "frontend": "https://open.qichacha.cn"},
    {"key": "TIANYANCHA_API_KEY", "name": "天眼查 API Key", "remark": "企业查询（工商信息）", "frontend": "https://open.tianyancha.com"},
    {"key": "YUNZHANGFANG_API_KEY", "name": "云账房 API Key", "remark": "云账房做账/申报对接", "frontend": ""},
    {"key": "YUNZHANGFANG_API_SECRET", "name": "云账房 API Secret", "remark": "云账房做账/申报对接", "frontend": ""},
    {"key": "LLM_API_KEY", "name": "AI 大模型 Key", "remark": "AI经营助手（DeepSeek/Qwen），留空则助手为演示模式", "frontend": ""},
    {"key": "LLM_BASE_URL", "name": "AI 大模型接口地址", "remark": "默认 https://api.deepseek.com/v1", "frontend": ""},
    {"key": "DINGTALK_APP_KEY", "name": "钉钉 AppKey", "remark": "通讯录同步", "frontend": ""},
    {"key": "DINGTALK_APP_SECRET", "name": "钉钉 AppSecret", "remark": "通讯录同步", "frontend": ""},
]


@api_view(["GET", "PUT"])
@permission_classes([permissions.IsAuthenticated])
def sys_config_view(request):
    """第三方API配置：GET 返回掩码后的配置；PUT 保存（仅老板/管理员）"""
    u = request.user
    if not (u.is_superuser or u.role in ("BOSS", "MANAGER")):
        return Response({"code": 1, "msg": "仅老板/管理员可管理第三方配置"}, status=status.HTTP_403_FORBIDDEN)
    if request.method == "GET":
        items = []
        for spec in SECRET_KEYS:
            raw = SystemConfig.get(spec["key"], "")
            # 掩码展示：只露出前4后4
            masked = (raw[:4] + "****" + raw[-4:]) if len(raw) > 8 else ("****" if raw else "")
            items.append({**spec, "configured": bool(raw), "masked": masked})
        return Response({"code": 0, "data": items,
                         "demo_mode": SystemConfig.get("DEMO_MODE", "") == "1"})
    # PUT
    data = request.data or {}
    saved = []
    for spec in SECRET_KEYS:
        k = spec["key"]
        if k in data and isinstance(data[k], str):
            v = data[k].strip()
            if "****" in v:  # 掩码未改动，跳过
                continue
            SystemConfig.set(k, v, remark=spec["name"], user=u)
            saved.append(k)
    if "demo_mode" in data:  # 演示模式开关（布尔）
        SystemConfig.set("DEMO_MODE", "1" if data["demo_mode"] else "", remark="演示模式全局只读开关", user=u)
        saved.append("DEMO_MODE")
    log_action(request, "UPDATE", module="系统配置", object_type="SystemConfig",
               detail="更新配置项: " + ",".join(saved))
    return Response({"code": 0, "msg": f"已保存 {len(saved)} 项配置（立即生效）", "saved": saved})


# 安全说明：密钥值不通过 HTTP 暴露。业务代码需要读取时直接
# `from apps.common.models import SystemConfig; SystemConfig.get("KEY", "")`。
