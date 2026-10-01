#!/bin/bash
# 财税企管云 · 生产版一键启动（最新构建 + 预览服务 4173）
# 用法：bash /Users/luosifu/WorkBuddy/2026-09-01-20-39-34/finops-cloud/finops-prod.sh [restart]
#
# 说明：
#   1) 先用最新源码重新构建 dist/
#   2) 再起 vite preview 服务到 127.0.0.1:4173（代理 /api、/media 到 Django 8000）
#   3) 打开浏览器
#
# 注意：本脚本只管【前端生产版】，Django 后端由 finops.sh 守护，不在本脚本内重启。

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
NODE_BIN=/Users/luosifu/.workbuddy/binaries/node/versions/22.12.0/bin
export PATH="$NODE_BIN:$PATH"
LOG="$ROOT/logs/preview.log"

# 停掉旧的预览服务
OLD=$(lsof -nP -iTCP:4173 -sTCP:LISTEN -t 2>/dev/null || true)
if [ -n "$OLD" ]; then
  echo "▶ 停止旧预览服务 (PID $OLD) ..."
  kill $OLD 2>/dev/null || true
  sleep 2
fi

echo "▶ 用最新源码重新构建 dist/ ..."
cd "$ROOT/web"
npm run build

echo "▶ 启动生产预览服务 (4173) ..."
mkdir -p "$ROOT/logs"
nohup npm run preview > "$LOG" 2>&1 &

echo "▶ 等待服务就绪..."
for i in $(seq 1 20); do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 http://127.0.0.1:4173/ || true)
  if [ "$CODE" = "200" ]; then break; fi
  sleep 1
done

open "http://127.0.0.1:4173" || true

echo ""
echo "✅ 财税企管云【生产最新版】已就绪"
echo "   生产版前端: http://127.0.0.1:4173   (dist/ 构建产物，本次重新构建)"
echo "   开发版前端: http://127.0.0.1:5173   (Vite dev，实时热更新)"
echo "   后端 Django: http://127.0.0.1:8000"
echo "   账号: admin   密码: admin123"
echo "   日志: $LOG"
echo ""
