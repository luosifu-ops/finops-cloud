# 财税企管云 · 后端容器镜像（CloudBase 云托管 / 通用容器）
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 生产静态文件收集（管理后台/媒体用，失败不阻断启动）
RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

# 启动：先迁移表结构，再用 gunicorn 监听容器端口
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120"]
