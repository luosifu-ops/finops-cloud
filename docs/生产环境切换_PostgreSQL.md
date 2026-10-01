# 财税企管云 · 生产 PostgreSQL 切换说明

> 当前线上（`https://7ec81e19ed6f4772859dc182a6b14c43.app.workbuddy.host`）为 **SQLite 预览态**：
> 沙箱重启即重置数据，仅用于功能/权限走查。正式交付需切换到 PostgreSQL。

## 一、代码侧已就绪（无需改代码）
- `config/settings.py` 第 89–91 行：检测到 `DATABASE_URL` 环境变量即走 PostgreSQL，否则回退 SQLite。
  ```python
  if os.environ.get("DATABASE_URL"):
      import dj_database_url
      DATABASES = {"default": dj_database_url.parse(os.environ["DATABASE_URL"], conn_max_age=600)}
  ```
- `requirements.txt`（完整版）已含 `psycopg2-binary==2.9.10`、`PyJWT`、`dj-database-url` 等；`dj_database_url` 仅在 `DATABASE_URL` 存在时 import，SQLite 模式下不影响。
- `start.sh` 已区分模式：`DATABASE_URL` 存在 → `gunicorn` 生产模式；否则 → `runserver` 预览模式（并播种演示账号）。

## 二、切换步骤（待 boss 提供 DATABASE_URL 后执行）
1. **准备 PostgreSQL 实例**：在 Neon（免费）或腾讯云 CloudBase 云托管 开通 Postgres，取得连接串，形如：
   `postgres://user:password@host:5432/dbname?sslmode=require`
2. **注入环境变量**：在当前发布应用的环境变量设置中设置 `DATABASE_URL=<上面的连接串>`。
   - ⚠️ **工具缺口**：`workbuddy_sites_deploy` 暂不支持在部署参数里传环境变量，因此 `DATABASE_URL` 需通过「发布应用的环境变量设置」界面填写（发布后在「设置—数据管理—我发布的应用」里找到本应用 → 环境变量）。
3. **使用完整 requirements**：部署前确保 `requirements.txt` 为完整版（含 `psycopg2-binary` 等 4 个外部/生产包），不要用预览版（已剥离的那份）。
4. **重新部署**：重发同一目录 `.../finops-cloud/backend`，`start.sh` 会自动 `migrate` + 以 gunicorn 启动生产模式。
5. **验证**：访问 `/admin/login/` 能进；API 返回 200；数据持久化（重启不再重置）。

## 三、可选增强（如需让 start.sh 直接读 .env）
若希望把 `DATABASE_URL` 写进项目而非依赖平台环境变量，可在 `start.sh` 开头加：
```sh
[ -f .env ] && set -a && . ./.env && set +a
```
并把 `.env` 加入部署忽略清单（避免把密钥提交进仓库）。**当前未实现**，待 boss 确认走「平台环境变量」还是「.env 文件」方案后再落地。

## 四、凭证缺口（需 boss 提供）
- [ ] PostgreSQL 连接串 `DATABASE_URL`（Neon / CloudBase Postgres）
- [ ] 确认走「平台环境变量」还是「.env 文件」注入方式
