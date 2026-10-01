#!/bin/bash
# 财税企管云 · PostgreSQL 定时备份脚本
# 用法：
#   手动执行： bash deploy/prod/backup.sh
#   定时任务： 把下面 "crontab 示例" 加进服务器（每天 03:30 备份，保留最近 7 天）
#
# 依赖：在运行本脚本的机器上能连到 PostgreSQL（同 docker 网络用服务名 db，
#        或填写真实 HOST/PORT）。推荐用 docker exec 进 db 容器或在本机装 pg_dump。

set -e

# ---------- 可改配置 ----------
BACKUP_DIR="${BACKUP_DIR:-/var/backups/finops}"
KEEP_DAYS="${KEEP_DAYS:-7}"
# 数据库凭据（与 docker-compose 的 POSTGRES_* 一致；生产请把这些值放进环境变量或 secrets，勿写死）
PG_HOST="${PG_HOST:-db}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${PG_USER:-finops}"
PG_DB="${PG_DB:-finops}"
# 若用容器外执行，可改用 POSTGRES_PASSWORD 环境变量传入，本脚本不打印
export PGPASSWORD="${PG_PASSWORD:-}"

# ---------- 执行 ----------
mkdir -p "$BACKUP_DIR"
TS="$(date +%Y%m%d_%H%M%S)"
OUT="$BACKUP_DIR/finops_${TS}.sql.gz"

echo "[backup] dumping ${PG_USER}@${PG_HOST}:${PG_PORT}/${PG_DB} -> $OUT"
pg_dump -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" \
  --no-owner --clean --if-exists | gzip > "$OUT"

echo "[backup] 完成，大小：$(du -h "$OUT" | cut -f1)"

# 清理旧备份
echo "[backup] 清理 ${KEEP_DAYS} 天前的备份..."
find "$BACKUP_DIR" -name 'finops_*.sql.gz' -mtime +"$KEEP_DAYS" -delete

echo "[backup] 当前保留："
ls -1 "$BACKUP_DIR" | tail -n 10

# ---------- crontab 示例（服务器上执行 crontab -e 粘贴下面一行） ----------
# 30 3 * * * PG_PASSWORD='你的强密码' BACKUP_DIR=/var/backups/finops bash /opt/finops-cloud/deploy/prod/backup.sh >> /var/backups/finops/backup.log 2>&1
