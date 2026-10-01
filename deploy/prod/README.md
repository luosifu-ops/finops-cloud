# 财税企管云 · 生产部署与备案保姆级手册（路线 B）

> 目标：把站点从「WorkBuddy 沙箱」迁移到「**自有域名 + 大陆服务器**」，使其**可ICP备案、可对外正式服务**。
> 本目录 `deploy/prod/` 已附带全部生产配置：生产安全设置、Docker 镜像、自动 HTTPS 网关、环境变量模板、启动脚本。
> 沙箱（路线 A）不受影响，继续可预览。

---

## 一、整体架构（部署后）

```
公网用户
   │  https://你的域名  (Caddy 自动申请 Let's Encrypt 证书)
   ▼
[Caddy 容器]  ← 自动 HTTPS / 反代
   ▼
[Django + gunicorn 容器]  ← /api/* REST + 前端 SPA，连 PostgreSQL
   ▼
[PostgreSQL 容器]  ← 业务数据（替代沙箱的 SQLite）
```

---

## 二、第 0 步：准备「备案前置三件套」（最耗时，先办）

> 这步不动代码，纯行政/采购，但**决定了后面能否备案**，务必先动手。

1. **买大陆服务器**：腾讯云「轻量应用服务器」或「云服务器 CVM」，地域选**中国大陆**（如上海/广州），系统 Ubuntu 22.04，配置 2C2G 起。
   - Boss 已有腾讯云账号 `lsf246891`（已实名），直接在控制台买即可。
2. **注册自有域名**：在腾讯云域名注册，选 `.com`/`.cn` 等，注册时**主体填「云南财税通集团有限公司」**（与备案主体一致，否则会被打回）。
3. **域名企业实名 + 解析**：域名控制台完成企业实名认证；解析一条 **A 记录**指向服务器公网 IP（部署完成后做也行，但备案初审前要有）。

> 备案主体 = **云南财税通集团有限公司**（统一社会信用代码 `91530103MABP04430B`，法人 **果元明**）。

---

## 三、第 1 步：服务器装 Docker（约 2 分钟）

SSH 登录服务器后，逐行复制执行：

```bash
# 一键安装 Docker + Compose 插件
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# 退出重登使 docker 权限生效，或执行：newgrp docker
docker --version && docker compose version
```

---

## 四、第 2 步：上传项目代码

```bash
# 方式A：git（若已托管）
git clone <你的仓库地址> finops-cloud && cd finops-cloud

# 方式B：本地打包上传
# 在本机执行：cd finops-cloud && tar czf finops.tar.gz --exclude=node_modules --exclude=.git --exclude=backend/db.sqlite3 .
# 再 scp 到服务器后 tar xzf 解压
```

---

## 五、第 3 步：填写生产环境变量

```bash
cd finops-cloud
cp deploy/prod/.env.example deploy/prod/.env
nano deploy/prod/.env        # 或 vim
```

**必填项**（其余留空走演示模式）：
- `SITE_DOMAIN` / `ALLOWED_HOSTS`：你的域名
- `DJANGO_SECRET_KEY`：执行 `openssl rand -hex 50` 生成后粘贴
- `DB_PASSWORD`：自定义强密码
- `CORS_ALLOWED_ORIGINS`：填 `https://你的域名`

---

## 六、第 4 步：一条命令启动

```bash
docker compose -f deploy/prod/docker-compose.yml --env-file deploy/prod/.env up -d --build
```

启动后查看状态与日志：
```bash
docker compose -f deploy/prod/docker-compose.yml ps
docker compose -f deploy/prod/docker-compose.yml logs -f web
```

---

## 七、第 5 步：验证上线

1. 浏览器打开 `https://你的域名` → 应显示登录页（地址栏有锁标）。
2. 用 `admin / admin123` 登录（**上线后务必改 admin 密码**）。
3. 逐模块点一遍：电销/会计/运营/增长中心/人事/会员等接口应正常返回数据。
4. 后台 `https://你的域名/admin/` 可访问。

> 若打不开：先 `docker compose ... logs web` 看是否 `DJANGO_SECRET_KEY`/`ALLOWED_HOSTS` 未设导致启动拒绝（settings_prod.py 会显式报错）。

---

## 八、第 6 步：ICP 备案（拿到域名+服务器后即可）

1. 腾讯云控制台 → **备案** → 选择「新增网站/首次备案」。
2. 按系统填：**主体信息**（营业执照、法人身份证）、**网站信息**（网站名、域名、服务内容）、**负责人**（身份证+核验照，APP 人脸核验）。
3. 上传材料 → 服务商初审（1-2 天）→ 收到**工信部短信核验码，24 小时内**完成核验。
4. 管局终审（**7-20 个工作日**）→ 下发备案号，格式如 `滇ICP备XXXXXXXX号-X`。
5. **把备案号挂到网站首页底部**，并链接至工信部查询系统（在 `web/src` 页脚组件加一行即可）。

> 若站点含「会员付费/微信支付」且**面向公众收费**，属经营性，须在备案后另办 **ICP 经营许可证**。
> 若仅作公司内部工具、不对外部收费，按**非经营性备案**即可（推荐口径，最稳）。

---

## 九、第 7 步：公安联网备案（上线 30 日内）

1. 打开 `https://beian.mps.gov.cn` → 注册 → 新增主体/网站。
2. 填主体、网站、应急联系人信息 → 提交 → 1-3 天审核。
3. 把公安备案编号 HTML 代码 + 图标放到网页底部，与 ICP 备案号并列。

---

## 十、第 8 步：接入真实能力（可选，按需）

在 `deploy/prod/.env` 填好下列变量后，重启容器即生效（`docker compose ... up -d`）。
所有真实接口均由代码内置 Key 网关控制：**未配置 Key 走演示数据，配置了 Key 才打真实接口，任何异常自动回退演示且不报错**。

| 能力 | 变量 | 效果 / 说明 |
|---|---|---|
| AI 经营助手 | `LLM_API_KEY` | 从演示模式变为真实大模型回答（`dashboard/ai/chat` 已接 OpenAI 兼容端点，默认 DeepSeek） |
| 微信 PC 扫码登录 | `WX_OPEN_APPID` / `WX_OPEN_SECRET` | 真实微信扫码登录（生产 `WX_SCAN_MOCK=False` 已默认关闭） |
| 微信支付 | `WECHAT_PAY_*` + `WECHAT_PAY_ENABLED=True` | 会员付费真实收款（NATIVE 扫码 / H5） |
| 企业工商查询（优先） | `TIANYANCHA_API_KEY` | 真实企业数据：天眼查 `icAdvanced`(搜索)+`icBaseInfo`(详情)，单 Key 即接入（`Authorization: token`） |
| 企业工商查询（备选） | `QICHACHA_API_KEY` + `QICHACHA_SECRET` | 真实企业数据：企查查开放平台，需 Key+Secret 做 md5 签名 |
| 抖音/短视频对标 | `DOUYIN_API_BASE` + `DOUYIN_API_KEY` | 真实请求你自建/购买的第三方数据端点（蝉妈妈/飞瓜/巨量算数均无免费公开 API） |
| 云账房 | `YUNZHANGFANG_API_KEY` | SaaS 无公开 API，保留演示数据 + 官方入口跳转 |

### 抖音端点约定（DOUYIN_API_BASE）
`douyin_account(q)` 在配置了 `DOUYIN_API_BASE` 时，会真实请求：
```
GET {DOUYIN_API_BASE}/account?q=<昵称或账号>
Authorization: Bearer <DOUYIN_API_KEY>
```
期望返回 JSON 字段：`nickname, douyin_id/account_id, fans, works, likes, growth_30d, gmv_30d, tags[], hot_videos[]`。
未配置或请求失败 → 自动回退演示数据，接口不报错。

### 真实能力的「降级」保证
全部真实接口以 try/except 包裹，调用失败/超时（8s）/解析异常都会回退到演示数据并标记 `source=demo`，**绝不会让前端出现 5xx**，可放心上线后逐步接入。

---

## 十一、生产安全清单（已内置，确认即可）

- ✅ `settings_prod.py`：强制 `SECRET_KEY`/`ALLOWED_HOSTS`、关闭 `DEBUG`、`WX_SCAN_MOCK=False`、CORS 收拢、Cookie `Secure`、whitenoise 静态。
- ✅ 全站 HTTPS（Caddy 自动证书）。
- ✅ 数据库迁 PostgreSQL（`DATABASE_URL` 环境变量，沙箱仍是 SQLite，互不影响）。
- ⚠️ 上线后**立即改 admin 密码**、按需关闭演示账号。
- ⚠️ 生产务必做**数据库定时备份**（PostgreSQL `pg_dump` 或云快照）。

---

## 附：裸机部署（不用 Docker）

> 推荐走上面的 Docker 编排（db+web+caddy 一条命令）。仅在确无 Docker 时用手动方式。

服务器已装好 Python 3.13 + PostgreSQL，并在 shell 中 export 好下列环境变量后：
`DJANGO_SETTINGS_MODULE=config.settings_prod`、`DATABASE_URL`、`DJANGO_SECRET_KEY`、`ALLOWED_HOSTS`、`DEBUG=False`、`CORS_ALLOWED_ORIGINS`，以及可选的 `LLM_API_KEY` / `WECHAT_PAY_*`。

```bash
cd /path/to/finops-cloud/backend
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
# 用 gunicorn 拉起（workers 可按 CPU 调），再用 nginx/Caddy 反代 8000 并配置 SSL
gunicorn -c deploy/prod/gunicorn.conf.py config.wsgi:application
```

> 裸机方式需自行保证静态文件（whitenoise）与媒体目录持久化、以及 HTTPS 证书续期。
