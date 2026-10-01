"""财税企管云 · 生产环境配置（继承基础配置，收紧安全项）

用法：部署时设置环境变量 DJANGO_SETTINGS_MODULE=config.settings_prod
本文件只做「生产化收紧」，不改动任何业务代码与基础配置。沙箱部署仍用 config.settings。
"""
from .settings import *  # noqa: F401,F403
import os

# ---------- 强制生产安全 ----------
# 生产必须关闭 DEBUG（部署时显式传 DEBUG=False；默认即是 False）
DEBUG = os.environ.get("DEBUG", "False") == "True"

# 强制密钥：未设置直接拒绝启动，杜绝使用开发占位密钥上线
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    raise RuntimeError("生产环境必须设置环境变量 DJANGO_SECRET_KEY（请用强随机值）")

# 强制域名白名单：不设置直接拒绝启动（避免 ALLOWED_HOSTS=["*"] 暴露到公网）
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()]
if not ALLOWED_HOSTS:
    raise RuntimeError("生产环境必须设置 ALLOWED_HOSTS（你的域名，多个用逗号分隔）")

# 微信扫码 mock 在生产环境默认关闭（避免任何人可模拟扫码登录）
WX_SCAN_MOCK = os.environ.get("WX_SCAN_MOCK", "False") == "True"

# ---------- CORS 收紧到自有域名 ----------
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()
]
CORS_ALLOW_CREDENTIALS = True

# ---------- Cookie / 会话安全（需 HTTPS） ----------
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in ALLOWED_HOSTS]

# 反向代理（nginx）下取真实信息
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ---------- 静态文件：whitenoise 直接服务（无需单独 nginx 静态块） ----------
# 部署前执行：python manage.py collectstatic --noinput
# 注意：whitenoise 只需中间件，不必加入 INSTALLED_APPS
MIDDLEWARE = (
    MIDDLEWARE[:1]
    + ["whitenoise.middleware.WhiteNoiseMiddleware"]
    + MIDDLEWARE[1:]
)
STATIC_ROOT = BASE_DIR / "staticfiles"
