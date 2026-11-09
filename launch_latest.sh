#!/bin/bash
# 财税企管云 · 最新代码版启动脚本（iCloud 副本 prod-2026-11-05b）
ROOT="/Users/luosifu/Library/Mobile Documents/com~apple~CloudDocs/桌面归档-20261107/AI项目/finops-cloud"
PY="/Users/luosifu/.workbuddy/binaries/python/envs/default/bin/python3"
NODE_BIN="/Users/luosifu/.workbuddy/binaries/node/versions/22.12.0/bin"
LOG="$ROOT/logs"
mkdir -p "$LOG"
for p in 8000 5173; do
  pids="$(/usr/sbin/lsof -ti tcp:$p 2>/dev/null || true)"
  [ -n "$pids" ] && kill $pids 2>/dev/null; sleep 1
done
cd "$ROOT/backend"
nohup "$PY" manage.py runserver 127.0.0.1:8000 --noreload >> "$LOG/backend.log" 2>&1 < /dev/null &
cd "$ROOT/web"
PATH="$NODE_BIN:$PATH" nohup npm run dev -- --host 127.0.0.1 --port 5173 >> "$LOG/frontend.log" 2>&1 < /dev/null &
exit 0
