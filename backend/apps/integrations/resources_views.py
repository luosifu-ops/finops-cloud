"""云资源对接配置 ViewSet（纯新增，复用 IsAuthenticated）
- 仅「管理层/老板/超管」可写，普通用户只读自身
- /check/ 健康检测走原生 stdlib HTTP/TCP 探活（不引入第三方 SDK）
"""
import socket
import ssl
import urllib.parse
import urllib.request
from datetime import datetime, timezone as dj_tz

from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.growth.permissions import can_view_all
from .models import CloudResourceConfig
from .serializers import CloudResourceConfigSerializer


def _is_resource_admin(user):
    """对接配置管理员：与 can_view_all 同口径（管理层+老板+超管）"""
    return can_view_all(user)


class CloudResourceConfigViewSet(viewsets.ModelViewSet):
    queryset = CloudResourceConfig.objects.filter(is_deleted=False)
    serializer_class = CloudResourceConfigSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["name", "endpoint", "bucket_or_instance"]
    ordering_fields = ["created_at"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsAuthenticated(), _ResourceAdminOnly()]

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get("provider"):
            qs = qs.filter(provider=p["provider"])
        if p.get("resource_type"):
            qs = qs.filter(resource_type=p["resource_type"])
        return qs.order_by("provider", "resource_type", "-created_at")

    @action(detail=True, methods=["post"])
    def check(self, request, pk=None):
        """健康检测：通过原生 HTTP/TCP 探活（不引入第三方中间商）
        - DOMAIN: HTTP HEAD
        - STORAGE/SERVER/DATABASE: TCP connect (port 443 默认)
        """
        cfg = self.get_object()
        url = (cfg.endpoint or "").strip()
        if not url:
            return Response({"detail": "endpoint 为空，请先配置"}, status=status.HTTP_400_BAD_REQUEST)

        ok = False
        msg = ""
        code = ""
        try:
            parsed = urllib.parse.urlparse(url)
            host = parsed.hostname
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            if cfg.resource_type == "DOMAIN":
                req = urllib.request.Request(url, method="HEAD")
                with urllib.request.urlopen(req, timeout=4) as r:
                    code = str(r.status)
                    ok = 200 <= r.status < 500
                    msg = f"HTTP {r.status} {r.reason}"
            else:
                ctx = ssl.create_default_context()
                with socket.create_connection((host, port), timeout=4) as sock:
                    if parsed.scheme == "https":
                        with ctx.wrap_socket(sock, server_hostname=host):
                            pass
                ok = True
                code = "0"
                msg = f"TCP {host}:{port} reachable"
        except Exception as e:  # noqa
            ok = False
            msg = f"{type(e).__name__}: {str(e)[:120]}"

        cfg.last_check_at = timezone.now()
        cfg.last_check_ok = ok
        cfg.last_check_msg = msg
        cfg.save(update_fields=["last_check_at", "last_check_ok", "last_check_msg"])

        return Response({
            "id": cfg.id, "ok": ok, "code": code, "msg": msg,
            "checked_at": cfg.last_check_at,
        })

    @action(detail=False, methods=["get"])
    def capacity(self, request):
        """按需扩容：返回当前总容量分布（按 provider / resource_type）"""
        qs = self.get_queryset().filter(capacity_gb__gt=0)
        rows = []
        for p in ("TENCENT", "ALI"):
            for rt in ("STORAGE", "SERVER", "DATABASE"):
                sub = qs.filter(provider=p, resource_type=rt)
                total_gb = sum(s.capacity_gb for s in sub)
                cap_gb = sum(s.capacity_max_gb or 0 for s in sub)
                rows.append({
                    "provider": p, "resource_type": rt,
                    "count": sub.count(),
                    "used_gb": total_gb,
                    "max_gb": cap_gb,
                    "expandable": cap_gb == 0 or total_gb < cap_gb,
                })
        return Response(rows)


from rest_framework.permissions import BasePermission


class _ResourceAdminOnly(BasePermission):
    """可写权限：仅管理层+老板+超管（HR/LEADER/EMPLOYEE 一律只读）"""

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return _is_resource_admin(u)
