#!/bin/bash
# 财税企管云 · 本机一键启动（Boss 的 M1 Mac 上运行）
# 用法：在终端执行  bash /Users/luosifu/WorkBuddy/2026-09-01-20-39-34/finops-cloud/start.sh
# 启动后浏览器自动打开 http://127.0.0.1:5173 ，用 admin / admin123 登录即可。
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
PY=/Users/luosifu/.workbuddy/binaries/python/envs/default/bin/python3
NODE_BIN=/Users/luosifu/.workbuddy/binaries/node/versions/22.12.0/bin
export PATH="$NODE_BIN:$PATH"

echo "▶ 启动后端 Django (8000) ..."
cd "$ROOT/backend"
"$PY" manage.py runserver 127.0.0.1:8000 --noreload &
BACK=$!

echo "▶ 启动前端 Vite (5173) ..."
cd "$ROOT/web"
npm run dev -- --host 127.0.0.1 --port 5173 &
FRONT=$!

echo "▶ 等待前端就绪..."
sleep 6
open http://127.0.0.1:5173 || echo "(请手动打开 http://127.0.0.1:5173)"

echo ""
echo "✅ 财税企管云已启动"
echo "   前端: http://127.0.0.1:5173   后端: http://127.0.0.1:8000"
echo "   账号: admin   密码: admin123"
echo "   按 Ctrl+C 退出（会同时关闭前后端）"
echo ""

# 捕获退出，清理子进程
cleanup() { kill $BACK $FRONT 2>/dev/null || true; exit 0; }
trap cleanup INT TERM
wait
