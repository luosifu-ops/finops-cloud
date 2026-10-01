#!/bin/bash
# 财税企管云 · 后台守护启动（由 launchd 调用，无终端、登录自启）
# 本脚本只负责把前后端以「脱离终端的独立会话」方式拉起，然后自行退出。
# launchd 不管理这两个子进程，因此它们不受终端关闭影响。
set -u
ROOT="/Users/luosifu/WorkBuddy/2026-09-01-20-39-34/finops-cloud"
PY="/Users/luosifu/.workbuddy/binaries/python/envs/default/bin/python3"
NODE_BIN="/Users/luosifu/.workbuddy/binaries/node/versions/22.12.0/bin"
LOG="$ROOT/logs"
mkdir -p "$LOG"

# 释放可能被旧实例占用的端口（避免新实例绑定失败）
for p in 8000 5173; do
  pids="$(/usr/sbin/lsof -ti tcp:$p 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    echo "$(date) 释放端口 $p (pid: $pids)" >> "$LOG/launch.log"
    kill $pids 2>/dev/null || true
    sleep 1
  fi
done

# 后端 Django（nohup 脱离终端；配合 plist 的 AbandonProcessGroup 长期存活）
cd "$ROOT/backend"
nohup "$PY" manage.py runserver 127.0.0.1:8000 --noreload \
  >> "$LOG/backend.log" 2>&1 < /dev/null &

# 前端 Vite
cd "$ROOT/web"
PATH="$NODE_BIN:$PATH" nohup npm run dev -- --host 127.0.0.1 --port 5173 \
  >> "$LOG/frontend.log" 2>&1 < /dev/null &

echo "$(date) 财税企管云已后台启动（前端 5173 / 后端 8000）" >> "$LOG/launch.log"
exit 0
