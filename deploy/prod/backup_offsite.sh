#!/bin/bash
# 财税企管云 · 异地备份脚本（在【服务器】上运行，适配 cron）
# ============================================================
# 设计：宿主机上通过 `docker compose exec db` 在数据库容器内 dump
#       （容器自带 pg_dump，可解析 db 服务名），再上传到「异地 COS」。
# 异地要点：COS 桶务必与服务器不同地域
#           （服务器成都 ap-chengdu → 桶建议用广州 ap-guangzhou / 上海 ap-shanghai）。
# 密钥只走环境变量 COS_SECRETID / COS_SECRETKEY，不写死。
# 注意：主 .env 含非 bash 兼容内容(如带空格/中文的值)，绝不可整文件 source；
#       本脚本只读取独立的 backup.env（bash 兼容，仅 COS 配置）。
# ============================================================
set -e

# 是否需 sudo（cron 以普通用户跑时 docker 需 root；以 root 跑时自动为空）
if [ "$(id -u)" -ne 0 ]; then SUDO="sudo"; else SUDO=""; fi

COMPOSE_FILE="${COMPOSE_FILE:-/opt/finops-cloud/deploy/prod/docker-compose.yml}"
ENV_FILE="${ENV_FILE:-/opt/finops-cloud/deploy/prod/.env}"
BACKUP_ENV="${BACKUP_ENV:-/opt/finops-cloud/deploy/prod/backup.env}"

# 仅加载备份专用的 COS 配置（独立文件，bash 兼容）
if [ -f "$BACKUP_ENV" ]; then
  set -a
  source "$BACKUP_ENV"
  set +a
fi

BACKUP_DIR="${BACKUP_DIR:-/var/backups/finops}"
KEEP_DAYS="${KEEP_DAYS:-7}"

COS_BUCKET="${COS_BUCKET:-}"
COS_REGION="${COS_REGION:-ap-guangzhou}"
COS_PREFIX="${COS_PREFIX:-finops-pg}"
COSCLI="${COSCLI:-coscli}"

mkdir -p "$BACKUP_DIR"
TS="$(date +%Y%m%d_%H%M%S)"
OUT="$BACKUP_DIR/finops_${TS}.sql.gz"

echo "[$(date)] [backup] 通过 db 容器 dump -> $OUT"
$SUDO docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T db \
  sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --clean --if-exists' \
  | gzip > "$OUT"
echo "[$(date)] [backup] 完成，大小：$(du -h "$OUT" | cut -f1)"

# 清理本机旧备份
find "$BACKUP_DIR" -name 'finops_*.sql.gz' -mtime +"$KEEP_DAYS" -delete

# 上传到异地 COS（密钥仅从 backup.env 读取，经命令行参数传给 coscli，实现单源）
if [ -z "$COS_BUCKET" ] || [ -z "$COS_SECRETID" ] || [ -z "$COS_SECRETKEY" ]; then
  echo "[$(date)] [backup][WARN] 未配置 COS_BUCKET/COS_SECRETID/COS_SECRETKEY，跳过异地上传（仅本地备份）"
else
  if "$COSCLI" cp "$OUT" "cos://${COS_BUCKET}/${COS_PREFIX}/$(basename "$OUT")" \
       -e "cos.${COS_REGION}.myqcloud.com" \
       -i "$COS_SECRETID" -k "$COS_SECRETKEY"; then
    echo "[$(date)] [backup] 已上传 cos://${COS_BUCKET}/${COS_PREFIX}/$(basename "$OUT")"
  else
    echo "[$(date)] [backup][WARN] COS 上传失败，本地备份仍保留：$OUT"
  fi
fi

echo "[$(date)] [backup] 本机保留："; ls -1 "$BACKUP_DIR" | tail -n 5
