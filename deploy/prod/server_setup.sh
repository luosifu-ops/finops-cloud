#!/bin/bash
# 财税企管云 · 新服务器一键部署脚本（Ubuntu 22.04）
# ============================================================
# 前置：
#   1) 你已在腾讯云买好【大陆】服务器（轻量/CVM，Ubuntu 22.04），并拿到公网 IP；
#   2) 已买好域名并解析 A 记录指向该 IP（备案初审前要有）；
#   3) 已把项目代码上传到服务器 /opt/finops-cloud
#      （本机打包： tar czf finops.tar.gz --exclude=node_modules --exclude=.git --exclude=backend/db.sqlite3 .
#        服务器解压： mkdir -p /opt/finops-cloud && tar xzf finops.tar.gz -C /opt/finops-cloud）
#
# 用法（SSH 进服务器后执行）：
#   cd /opt/finops-cloud
#   bash deploy/prod/server_setup.sh
# 脚本会：装 Docker → 生成 .env 强随机密钥（你再手动补 SITE_DOMAIN/域名）→ 起服务。
# ============================================================
set -e

echo "== 1/4 安装 Docker =="
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER"
  echo "⚠️ Docker 已装，请重新 SSH 登录使 docker 权限生效，再重跑本脚本。"
  echo "   或执行： newgrp docker"
  exit 0
fi
docker --version && docker compose version

echo "== 2/4 准备生产环境变量 =="
cd /opt/finops-cloud
if [ ! -f deploy/prod/.env ]; then
  cp deploy/prod/.env.example deploy/prod/.env
  # 生成强随机密钥，避免占位值导致启动拒绝
  sed -i "s#__CHANGE_ME_TO_A_LONG_RANDOM_STRING__#$(openssl rand -hex 50)#" deploy/prod/.env
  sed -i "s#__CHANGE_ME_STRONG_DB_PASSWORD__#$(openssl rand -hex 16)#" deploy/prod/.env
  echo "✅ 已生成 .env，DJANGO_SECRET_KEY / DB_PASSWORD 已填强随机值"
else
  echo "ℹ️  deploy/prod/.env 已存在，跳过生成"
fi

echo "== 3/4 请确认 .env 中的必填项 =="
echo "   必须改成你的真实值："
echo "     SITE_DOMAIN=你的域名（如 finops.your-company.com）"
echo "     ALLOWED_HOSTS=你的域名,www.你的域名"
echo "     CORS_ALLOWED_ORIGINS=https://你的域名"
echo "   编辑命令： nano deploy/prod/.env"
echo "   改完后执行第 4 步。"

echo "== 4/4 启动（确认 .env 无误后执行） =="
echo "   docker compose -f deploy/prod/docker-compose.yml --env-file deploy/prod/.env up -d --build"
echo "   查看状态： docker compose -f deploy/prod/docker-compose.yml ps"
echo "   查看日志： docker compose -f deploy/prod/docker-compose.yml logs -f web"
echo ""
echo "✅ 启动后浏览器开 https://你的域名 应显示登录页（地址栏带锁标）。"
echo "   登录 admin/admin123，上线后务必改 admin 密码。"
echo "   备案：腾讯云控制台 → 备案 → 按提示提交（免费）。"
