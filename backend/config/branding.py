"""财税企管云 · 品牌（白标）公开接口

无需登录即可访问，供前端在启动时拉取并应用到标题 / 侧边栏 / 登录页 / 会员页。
私有化交付给同行时，只需在部署环境变量里改 BRAND_NAME / BRAND_LOGO_CHAR /
BRAND_SUBTITLE 即可整体换皮，无需改代码。
"""
from django.conf import settings
from django.http import JsonResponse


def branding_view(request):
    return JsonResponse(
        {
            "name": getattr(settings, "BRAND_NAME", "财税企管云"),
            "logo_char": getattr(settings, "BRAND_LOGO_CHAR", "财"),
            "subtitle": getattr(settings, "BRAND_SUBTITLE", "代账公司 · 一体化智能管理平台"),
            "icp_beian": getattr(settings, "ICP_BEIAN", ""),
            "police_beian": getattr(settings, "POLICE_BEIAN", ""),
        }
    )
