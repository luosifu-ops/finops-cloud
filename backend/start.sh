#!/bin/sh
# 财税企管云 · 单端口启动脚本
# 用途：本地预览 / 发布沙箱 / CloudBase 云托管 通用
# - 监听 $PORT 并绑定 0.0.0.0（发布工具与云托管都会注入 PORT）
# - 有 DATABASE_URL 环境变量 => 生产模式(PostgreSQL + gunicorn)
# - 无 DATABASE_URL        => 本地/预览模式(SQLite + runserver)，行为与原预览完全一致
set -e

PORT=${PORT:-8000}

echo "[finops] 执行数据库迁移..."
python manage.py migrate --noinput

echo "[finops] 确保超级管理员 admin 存在(登录账号 admin / ${ADMIN_PASS:-admin123})..."
export DJANGO_SUPERUSER_USERNAME=${ADMIN_USER:-admin}
export DJANGO_SUPERUSER_PASSWORD=${ADMIN_PASS:-admin123}
export DJANGO_SUPERUSER_EMAIL=${ADMIN_USER:-admin}@company.com
python manage.py createsuperuser --noinput 2>/dev/null || echo "[finops] admin 账号已存在，跳过创建"

# 预览/本地模式（无 DATABASE_URL）：播种 4 大新模块走查用的演示角色账号
# （幂等，仅创建缺失账号；生产 PostgreSQL 模式不执行，避免污染真实数据）
if [ -z "$DATABASE_URL" ]; then
  echo "[finops] 预览模式：同步公司组织架构树（钉钉架构图）..."
  python manage.py seed_org_tree || echo "[finops] 组织架构播种跳过(无影响)"
  echo "[finops] 预览模式：初始化演示角色账号（线索录入/合同名录/外勤增值/人事架构 走查用）..."
  python manage.py seed_growth_roles || echo "[finops] 演示账号播种跳过(无影响)"
  echo "[finops] 预览模式：填充公司简介与企业文化..."
  python manage.py seed_company_profile || echo "[finops] 公司简介播种跳过(无影响)"
  echo "[finops] 预览模式：播种专业基础知识文章 + 题库/考试..."
  python manage.py seed_knowledge || echo "[finops] 知识库播种跳过(无影响)"
  echo "[finops] 预览模式：播种会计部演示数据（基础税种 + 纳税申报）..."
  python manage.py seed_accounting || echo "[finops] 会计部播种跳过(无影响)"
fi

if [ -n "$DATABASE_URL" ]; then
  echo "[finops] 生产模式(PostgreSQL) -> gunicorn 0.0.0.0:${PORT}"
  exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT} --workers 2 --timeout 120
else
  echo "[finops] 预览/本地模式(SQLite) -> runserver 0.0.0.0:${PORT}"
  exec python manage.py runserver 0.0.0.0:${PORT} --noreload
fi
