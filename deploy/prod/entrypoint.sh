#!/bin/bash
# 生产容器启动入口：收集静态 -> 迁移数据库 -> 拉起 gunicorn
set -e

cd /app
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings_prod}"

echo "[prod] collectstatic ..."
python manage.py collectstatic --noinput

echo "[prod] migrate ..."
python manage.py migrate --noinput

echo "[prod] 线索池打通（幂等，已存在则跳过）..."
python manage.py backfill_lead_ext || true

echo "[prod] 启动 gunicorn on :8000"
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
