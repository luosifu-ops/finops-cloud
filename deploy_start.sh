#!/bin/bash
# 财税企管云 · 部署沙箱启动脚本（由 WorkBuddy 部署工具调用）
# 单端口 Django 服务：同一端口同时提供 /api/* REST 接口 与 backend/spa/ 前端生产构建
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/backend"

# 选择 python 解释器
PYBIN="$(command -v python3 || command -v python)"

# 1) 安装 Python 依赖（部署工具 installCmd 通常已装，这里兜底）
"$PYBIN" -m pip install -r requirements.txt >/dev/null 2>&1 || true

# 2) 确保前端生产构建存在（若上传包未包含 backend/spa 产物，则现场构建）
if [ ! -f spa/index.html ]; then
  echo "[deploy] 未检测到 spa 产物，现场构建前端..."
  ( cd "$ROOT/web" && npm install && npm run build )
fi

# 3) 数据库迁移（幂等，缺失表则创建）
"$PYBIN" manage.py migrate --noinput

# 4) 仅当数据库为空（全新沙箱）时播种演示数据；已含数据则跳过，避免重复造数
NEED_SEED="$("$PYBIN" -c "import os,django; os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings'); django.setup(); from django.contrib.auth import get_user_model; print('1' if get_user_model().objects.count()==0 else '0')" 2>/dev/null || echo "1")"
if [ "$NEED_SEED" = "1" ]; then
  echo "[deploy] 数据库为空，播种演示数据..."
  "$PYBIN" manage.py seed_org_tree || true
  "$PYBIN" manage.py seed_growth_roles || true
  "$PYBIN" manage.py seed_company_profile || true
  "$PYBIN" manage.py seed_knowledge || true
  "$PYBIN" manage.py seed_accounting || true
else
  echo "[deploy] 数据库已含数据，跳过播种；仍确保会计部申报种子存在..."
  "$PYBIN" manage.py seed_accounting || true
fi

# 4.5) 打通线索池：为没有 LeadExt 的历史 sales.Lead 补建扩展记录（幂等，已存在则跳过）
#      确保「运营部老线索池」与「增长中心线索池」合并为一个统一池，历史数据不丢失
"$PYBIN" manage.py backfill_lead_ext || true

# 5) 单端口启动（绑定 0.0.0.0，监听 $PORT）
exec "$PYBIN" manage.py runserver 0.0.0.0:"${PORT:-8000}" --noreload
