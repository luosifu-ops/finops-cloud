"""
财税企管云 · Django 全局配置
本地默认 SQLite，生产通过环境变量 DATABASE_URL 切 PostgreSQL（Neon / CloudBase）
"""
import os
from pathlib import Path
from datetime import timedelta

# 若使用 MySQL（如 CloudBase 云数据库），用 PyMySQL 作为驱动，无需系统依赖
# Django 5.x 的 MySQL 后端强制校验 mysqlclient>=2.2.1，这里把 PyMySQL 版本号伪装为兼容值
if os.environ.get("DATABASE_URL", "").startswith("mysql"):
    try:
        import pymysql
        pymysql.version_info = (2, 2, 1, "final", 0)
        pymysql.install_as_MySQLdb()
    except ImportError:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent

# 加载 .env（本地开发 / 沙箱预览用，密钥不进版本库；生产/CI 用真实环境变量覆盖）
# 同时尝试 backend/.env 与 cwd 下的 .env，确保 manage.py 与部署脚本都能读到
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
    load_dotenv()
except Exception:  # noqa: 没有 python-dotenv 或被忽略时静默跳过
    pass

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-9f3k2m-dev-only-change-me-in-prod")
DEBUG = os.environ.get("DEBUG", "True") == "True"
ALLOWED_HOSTS = ["*"]

# ---------- 应用 ----------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
THIRD_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
]
LOCAL_APPS = [
    "apps.common",
    "apps.accounts",
    "apps.onboarding",
    "apps.hr",
    "apps.reports",
    "apps.sales",
    "apps.accounting",
    "apps.ops",
    "apps.dashboard",
    "apps.integrations",
    "apps.membership",
    "apps.investment",
    "apps.contracts",
    # 增长中心（纯增量新增：多平台线索流转 / 3570阶段 / 外勤 / 增值业务部 / 投放统计）
    "apps.growth",
    # 公司通知公告（纯增量新增：发布通知 / 发布文件 / 已读回执）
    "apps.notices",
]
INSTALLED_APPS = DJANGO_APPS + THIRD_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.common.middleware.DemoModeMiddleware",  # 演示模式全局只读开关（2026-10-29）
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------- 数据库 ----------
if os.environ.get("DATABASE_URL"):
    import dj_database_url  # noqa
    DATABASES = {"default": dj_database_url.parse(os.environ["DATABASE_URL"], conn_max_age=600)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 6}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------- 国际化 ----------
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------- DRF ----------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "config.jwt_auth.GatewaySafeJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": (
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DATETIME_FORMAT": "%Y-%m-%d %H:%M:%S",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=12),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ---------- CORS ----------
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# ---------- 业务常量 ----------
DEPT_SALES = "SALES"        # 电销部
DEPT_ACCOUNTING = "ACCOUNT"  # 会计部
DEPT_OPS = "OPS"             # 运营部
DEPT_MANAGEMENT = "MGMT"     # 管理层/综合部

AD_PLATFORMS = ["AMAP", "BAIDU", "XIAOHONGSHU", "DOUYIN", "KUAISHOU", "WECHAT", "OFFLINE"]

# ---------- 微信（网站应用扫码登录 / 小程序登录）----------
# 微信开放平台「网站应用」AppID / AppSecret（用于 PC 网站扫码登录）
WX_OPEN_APPID = os.environ.get("WX_OPEN_APPID", "")
WX_OPEN_SECRET = os.environ.get("WX_OPEN_SECRET", "")
# 扫码后微信回跳地址（必须是开放平台后台配置的可信域名下的地址）
WX_OPEN_REDIRECT_URI = os.environ.get(
    "WX_OPEN_REDIRECT_URI", "http://127.0.0.1:8000/api/accounts/auth/wx-scan/callback/"
)
# 小程序 AppID（wx.login 换 openid 用，生产环境应由 code 调 wx 接口换取）
WX_MINI_APPID = os.environ.get("WX_MINI_APPID", "")
WX_MINI_SECRET = os.environ.get("WX_MINI_SECRET", "")
# 未配置微信凭证时，是否允许「模拟扫码登录」（仅开发/演示用，生产务必关闭）
WX_SCAN_MOCK = os.environ.get("WX_SCAN_MOCK", "True") == "True"

# ---------- AI 经营助手（大模型配置）----------
# 任何 OpenAI 兼容端点都可以：DeepSeek、通义千问 Qwen（compatible-mode）、智谱、月之暗面等
# 国内访问推荐 DeepSeek（https://api.deepseek.com/v1）或 Qwen（compatible-mode）。
# 把 API Key 填到环境变量 LLM_API_KEY 即激活真模型，留空则前端显示「演示模式」+ 模板回答。
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")  # DeepSeek: deepseek-chat；Qwen: qwen-plus
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "30"))

# ---------- 外部能力集成（企查查/天眼查、抖音数据、云账房）----------
# 企业工商查询：企查查 / 天眼查 API Key（二选一即可激活真实数据，留空则为演示数据）
QICHACHA_API_KEY = os.environ.get("QICHACHA_API_KEY", "")
TIANYANCHA_API_KEY = os.environ.get("TIANYANCHA_API_KEY", "")
# 抖音数据（蝉妈妈 / 飞瓜 / 巨量算数等）API Key
DOUYIN_API_KEY = os.environ.get("DOUYIN_API_KEY", "")
# 云账房开放平台 API Key（用于拉取真实账套/凭证/报表）
YUNZHANGFANG_API_KEY = os.environ.get("YUNZHANGFANG_API_KEY", "")

# ---------- 微信支付（真实收款：NATIVE 扫码 + MWEB H5 跳转）----------
# 三项凭证填齐且 ENABLED=True 后，前端「微信支付」会调用统一下单接口，
# 返回真实可收款的 code_url（微信扫一扫拉起收银台）/ mweb_url（手机浏览器跳转微信支付）。
# 凭证获取：微信支付商户平台 → 产品中心开通「Native 支付」「H5 支付」，
#   APP_ID = 绑定的公众号/小程序 AppID（或商户平台「AppID 账号管理」绑定的 AppID）
#   MCH_ID = 微信支付商户号（10 位数字）
#   API_KEY = APIv2 密钥（商户平台 → API 安全 → 设置 APIv2 密钥，32 位）
# 未配置或未开启时，前端自动回退到系统内置「演示支付页」，不影响其他功能。
WECHAT_PAY = {
    "APP_ID": os.environ.get("WECHAT_PAY_APPID", ""),
    "MCH_ID": os.environ.get("WECHAT_PAY_MCH_ID", ""),
    "API_KEY": os.environ.get("WECHAT_PAY_API_KEY", ""),
    "ENABLED": os.environ.get("WECHAT_PAY_ENABLED", "False") == "True",
}

# 站点公网基址：用于拼接支付回跳 / 微信支付异步通知回调等绝对地址。
# 部署到公网后务必设置为对外可访问的域名（如 https://your.domain），
# 否则后端用内部代理地址拼接的 notify_url 微信无法回调用。留空则自动取请求 Host。
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "").rstrip("/")

# ---------- 品牌（私有化白标，卖给同行时按客户改）----------
# 三个变量均可通过环境变量覆盖；不设置则保持默认「财税企管云」。
# 前端在启动时拉取 /api/branding/ 并应用到标题 / 侧边栏 / 登录页 / 会员页。
BRAND_NAME = os.environ.get("BRAND_NAME", "财税企管云")
BRAND_LOGO_CHAR = os.environ.get("BRAND_LOGO_CHAR", "财")  # 侧边栏/登录页的小方块字符
BRAND_SUBTITLE = os.environ.get("BRAND_SUBTITLE", "代账公司 · 一体化智能管理平台")

# 备案号（备案通过后填写，前端页脚展示；留空则不显示）
ICP_BEIAN = os.environ.get("ICP_BEIAN", "")       # 如：滇ICP备XXXXXXXX号-X
POLICE_BEIAN = os.environ.get("POLICE_BEIAN", "")  # 公安联网备案号

# ---------- 微信小程序（openid 绑定 + 一次性订阅消息推送）----------
# 2026-10-02 增量，纯新增：未配置时所有调用静默跳过，不影响任何既有流程。
# ⚠️ 关于认证：**一次性订阅消息不需要微信认证**（企业/个人主体均可）；
#    只有「长期订阅消息」才要求行业资质 + 微信认证。故未认证也能用本能力。
# 凭证获取：mp.weixin.qq.com → 开发 → 开发管理 → 开发设置（AppID / AppSecret）
# 模板获取：mp.weixin.qq.com → 订阅消息 → 我的模板 → 选用后复制「模板ID」，
#          填到下面的 WX_TMPL_APPROVAL_RESULT（审批结果通知）。
WECHAT_MINI = {
    "APPID": os.environ.get("WX_MINI_APPID", ""),
    "SECRET": os.environ.get("WX_MINI_SECRET", ""),
    "ENABLED": os.environ.get("WX_MINI_ENABLED", "False") == "True",
    "STATE": os.environ.get("WX_MINI_STATE", "formal"),  # formal=正式版 / trial=体验版
    "TEMPLATES": {
        # 审批结果通知（请假/报销/加班等通用）
        "APPROVAL_RESULT": os.environ.get("WX_TMPL_APPROVAL_RESULT", ""),
    },
}

# ---------- 钉钉企业内部应用（HR 通讯录同步，2026-10-28 增量）----------
# 设计原则同微信/短信：未配置凭证时全部静默降级，绝不影响主流程。
# 凭证获取：钉钉管理后台 → 应用开发 → 创建企业内部应用（H5微应用）→ 凭证与基础信息（AppKey/AppSecret）
# 权限要求（应用后台「权限管理」开通）：通讯录部门信息读权限 + 通讯录部门成员读权限
DINGTALK = {
    "APP_KEY": os.environ.get("DINGTALK_APP_KEY", ""),
    "APP_SECRET": os.environ.get("DINGTALK_APP_SECRET", ""),
    "AGENT_ID": os.environ.get("DINGTALK_AGENT_ID", ""),
}
