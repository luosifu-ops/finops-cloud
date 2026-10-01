# 财税企管云 · 生产镜像（Django + gunicorn + whitenoise）
# 构建上下文必须是项目根目录（deploy/prod 的上一级），以便 COPY backend 与 deploy/prod
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 国内镜像加速（腾讯云内网极快）：apt 走 Debian 镜像，pip 走 PyPI 镜像
RUN sed -i 's|deb.debian.org|mirrors.tencent.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|deb.debian.org|mirrors.tencent.com|g' /etc/apt/sources.list 2>/dev/null || true
ENV PIP_INDEX_URL=https://mirrors.tencent.com/pypi/simple/ \
    PIP_TRUSTED_HOST=mirrors.tencent.com

WORKDIR /app

# 系统依赖：PostgreSQL 驱动编译需要 gcc/libpq
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 业务代码 + 生产启动脚本
COPY backend /app
COPY deploy/prod/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
