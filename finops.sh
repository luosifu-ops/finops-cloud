#!/bin/bash
# 财税企管云 · 服务管理（无需保持终端）
# 用法：bash finops.sh {start|stop|restart|status}
ROOT="/Users/luosifu/WorkBuddy/2026-09-01-20-39-34/finops-cloud"
PLIST="/Users/luosifu/Library/LaunchAgents/com.finops.cloud.plist"
DOMAIN="gui/$(id -u)"

case "${1:-status}" in
  start)
    if launchctl load "$PLIST" 2>/dev/null; then
      echo "✅ 已注册为『登录自启』后台守护（以后开机自动运行）"
    else
      echo "⚠️ launchctl 注册失败，改为『后台脱离』启动（本次有效，重启 Mac 后需重跑此命令）"
      nohup bash "$ROOT/launch.sh" >/dev/null 2>&1 &
    fi
    sleep 5
    echo "▶ 已启动。浏览器打开：http://127.0.0.1:5173  （账号 admin / admin123）"
    ;;
  stop)
    launchctl unload "$PLIST" 2>/dev/null
    for p in 8000 5173; do
      pid="$(/usr/sbin/lsof -ti tcp:$p 2>/dev/null || true)"
      [ -n "$pid" ] && kill $pid 2>/dev/null
    done
    echo "■ 已停止"
    ;;
  restart)
    "$0" stop; sleep 2; "$0" start
    ;;
  status)
    echo -n "前端 5173: "; curl -s -o /dev/null -w "%{http_code}\n" --max-time 4 http://127.0.0.1:5173/ 2>/dev/null || echo "无响应"
    echo -n "后端 8000: "; curl -s -o /dev/null -w "%{http_code}\n" --max-time 4 http://127.0.0.1:8000/api/dashboard/todo/ 2>/dev/null || echo "无响应"
    ;;
  *)
    echo "用法: bash finops.sh {start|stop|restart|status}"
    ;;
esac
