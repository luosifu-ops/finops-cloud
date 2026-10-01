#!/bin/bash
# 财税企管云 · 裸机（非 Docker）生产启动脚本
# 适用：已在服务器装好 Python 3.13 + PostgreSQL，并export 好环境变量后直接跑
#   export DJANGO_SETTINGS_MODULE=config.settings_prod
#   export DATABASE_URL=postgres://finops:密码@127.0.0.1:5432/finops
#   export DJANGO_SECRET_KEY=...  ALLOWED_HOSTS=你的域名  DEBUG=False
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT/backend"
PYBIN="$(command -v python3 || command -v python)"

echo "[prod] 安装依赖..."
"$PYBIN" -m pip install -r requirements.txt

echo "[prod] 收集静态..."
"$PYBIN" manage.py collectstatic --noinput

echo "[prod] 迁移数据库..."
"$PYBIN" manage.py migrate --noinput

echo "[prod] 线索池打通（幂等）..."
"$PYBIN" manage.py backfill_lead_ext || true

echo "[prod] 启动 gunicorn :8000（前置 nginx/Caddy 反代请自行配置 SSL）..."
exec "$PYBIN" -m gunicorn -c "$ROOT/deploy/prod/gunicorn.conf.py" config.wsgi:application
