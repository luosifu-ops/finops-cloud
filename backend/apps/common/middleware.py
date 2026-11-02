"""演示模式中间件（2026-10-29 Boss 全局规则：演示模式全局开关）。

在系统配置 DEMO_MODE=1 时：
- 普通用户的写操作（POST/PUT/PATCH/DELETE）被拦截，返回"演示模式"提示；
- BOSS/超管不受影响（可继续操作后台）；
- 登录/注册/健康检查等白名单路径不受影响；
- 所有读操作（GET/HEAD/OPTIONS）不受影响。

开关位置：系统管理 → 第三方API配置 → 演示模式。
"""
from django.utils.deprecation import MiddlewareMixin
from rest_framework.response import Response
from rest_framework import status

# 这些前缀不拦截（登录、自助入职、品牌信息、前端页面）
ALLOW_PREFIXES = (
    "/api/accounts/auth/",        # 登录/短信/微信
    "/api/apply",                 # 自助入职
    "/api/branding",
    "/admin/login",
    "/static/",
    "/spa/",
)

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

_demo_cache_ts = 0.0
_demo_cache_val = False


class DemoModeMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.method not in WRITE_METHODS:
            return None
        path = request.path or ""
        if any(path.startswith(p) for p in ALLOW_PREFIXES):
            return None
        # 只拦 API 写操作；BOSS/超管放行
        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            if user.is_superuser or getattr(user, "role", "") == "BOSS":
                return None
        else:
            return None  # 未认证的写请求由权限层自行处理
        # 延迟导入避免循环；带 5 秒缓存避免每个写请求都查库
        import time as _time
        from apps.common.models import SystemConfig
        global _demo_cache_ts, _demo_cache_val
        if _time.time() - _demo_cache_ts > 5:
            _demo_cache_val = SystemConfig.get("DEMO_MODE", "") == "1"
            _demo_cache_ts = _time.time()
        if _demo_cache_val:
            return Response(
                {"code": 1, "msg": "当前处于演示模式，已开启全局只读保护；如需操作请联系管理员关闭演示模式"},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None
