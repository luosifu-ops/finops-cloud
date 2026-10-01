#!/bin/bash
# 财税企管云 · 双击启动（本机跑后端，前端复用已运行的 vite）
# 双击后：终端跑后端 → 自动打开浏览器 http://127.0.0.1:5173 → 登录 admin / admin123
PY=/Users/luosifu/.workbuddy/binaries/python/envs/default/bin/python3
"$PY" /Users/luosifu/WorkBuddy/2026-09-01-20-39-34/finops-cloud/backend/manage.py runserver 127.0.0.1:8000 --noreload &
BACK=$!
sleep 5
open http://127.0.0.1:5173
echo "✅ 后端已启动，浏览器应已打开 5173。按 Ctrl+C 退出。"
wait $BACK
