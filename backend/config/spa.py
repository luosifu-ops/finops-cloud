"""财税企管云 · 单端口 SPA 托管

让 Django 在同一端口同时提供 REST API（/api/*）与前端页面（Vue 生产构建产物）。
- 真实存在的静态文件（assets/*.js|css|png…）按扩展名返回正确 Content-Type；
- 其余路径（客户端路由，如 /sales/payroll）一律回退到 index.html，交给前端路由接管。
依赖 DEBUG 与否均可用，部署沙箱（非 DEBUG）同样工作。
"""
import os

from django.conf import settings
from django.http import FileResponse, HttpResponse

SPA_ROOT = os.path.join(settings.BASE_DIR, "spa")

_CONTENT_TYPES = {
    ".js": "application/javascript; charset=utf-8",
    ".mjs": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".eot": "application/vnd.ms-fontobject",
    ".map": "application/json; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
}


def _content_type(filename):
    ext = os.path.splitext(filename)[1].lower()
    return _CONTENT_TYPES.get(ext, "application/octet-stream")


def spa_view(request, path=""):
    """SPA 统一入口：真实文件直接返回，其余回退 index.html。"""
    rel = (path or "").lstrip("/")

    # 1) 命中真实静态资源
    if rel:
        candidate = os.path.join(SPA_ROOT, rel)
        # 防目录穿越：归一化后必须仍在 SPA_ROOT 内
        if os.path.isfile(candidate) and os.path.abspath(candidate).startswith(
            os.path.abspath(SPA_ROOT)
        ):
            return FileResponse(
                open(candidate, "rb"), content_type=_content_type(rel)
            )

    # 2) SPA 回退：交给前端路由
    index_path = os.path.join(SPA_ROOT, "index.html")
    try:
        with open(index_path, "rb") as f:
            return HttpResponse(f.read(), content_type="text/html; charset=utf-8")
    except FileNotFoundError:
        return HttpResponse(
            "前端资源未找到：请先执行前端构建并将产物放入 backend/spa/。",
            status=500,
            content_type="text/plain; charset=utf-8",
        )
