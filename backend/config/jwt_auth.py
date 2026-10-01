"""网关安全的 JWT 认证。

部署到公网（CloudStudio Gateway 等反向代理）时有两个坑：
1. 网关会给每个请求注入它自己的 Bearer 令牌，导致匿名接口（登录等）被误拦；
2. 网关会剥离/替换客户端发来的 Authorization 头，导致登录后所有需鉴权的
   接口都拿不到用户令牌 → 401。

对策：
- 校验失败的令牌按「匿名」处理（不抛 401）；
- 鉴权令牌兜底从 Cookie（finops_access）读取，因为网关会透传 Cookie，
  但会动 Authorization 头。前端无需改动：登录响应由后端 Set-Cookie，
  浏览器后续请求自动携带；本地无网关时仍走 Authorization 头。

注意：本模块只依赖 rest_framework_simplejwt.authentication，不要在顶层
导入 rest_framework_simplejwt.views（会触发 DRF 在导入期解析认证类形成
循环导入）。刷新视图在 config/urls.py 中定义。
"""
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

ACCESS_COOKIE = "finops_access"
REFRESH_COOKIE = "finops_refresh"
ACCESS_MAX_AGE = 60 * 60 * 12        # 12h，与 ACCESS_TOKEN_LIFETIME 对齐
REFRESH_MAX_AGE = 60 * 60 * 24 * 7  # 7d，与 REFRESH_TOKEN_LIFETIME 对齐


def set_auth_cookies(response, token_data):
    """把 access / refresh 写入 Cookie（httponly=False 便于前端读取与续期）。"""
    response.set_cookie(
        ACCESS_COOKIE,
        token_data.get("access", ""),
        max_age=ACCESS_MAX_AGE,
        httponly=False,
        samesite="Lax",
    )
    if token_data.get("refresh"):
        response.set_cookie(
            REFRESH_COOKIE,
            token_data.get("refresh", ""),
            max_age=REFRESH_MAX_AGE,
            httponly=False,
            samesite="Lax",
        )
    return response


class GatewaySafeJWTAuthentication(JWTAuthentication):
    """优先 Authorization 头；缺失或无效时回退 Cookie。"""

    def authenticate(self, request):
        # 1) 标准 Authorization 头（本地 / 无网关场景）
        try:
            header_result = super().authenticate(request)
            if header_result is not None:
                return header_result
        except AuthenticationFailed:
            pass

        # 2) 回退到 Cookie（公网网关会透传 Cookie，但会剥离 Authorization 头）
        raw_token = request.COOKIES.get(ACCESS_COOKIE)
        if raw_token:
            try:
                validated_token = self.get_validated_token(raw_token)
            except AuthenticationFailed:
                return None
            user = self.get_user(validated_token)
            return (user, validated_token)

        return None
