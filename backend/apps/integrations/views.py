from rest_framework.decorators import api_view
from rest_framework.response import Response
from apps.common.response import ok, fail
from . import services


@api_view(["GET"])
def enterprise_search(request):
    try:
        params = {
            "q": request.GET.get("q", ""),
            "name": request.GET.get("name", ""),
            "legal": request.GET.get("legal", ""),
            "phone": request.GET.get("phone", ""),
            "credit_code": request.GET.get("credit_code", ""),
        }
        return Response(ok(services.search_enterprise(params)))
    except Exception as e:  # noqa
        return Response(fail(str(e)))


@api_view(["GET"])
def enterprise_detail(request, credit_code):
    try:
        return Response(ok(services.enterprise_detail(credit_code)))
    except Exception as e:  # noqa
        return Response(fail(str(e)))


@api_view(["GET"])
def douyin_account(request):
    try:
        q = request.GET.get("q", "")
        data = services.douyin_account(q)
        if not data:
            return Response(fail("请提供抖音号或昵称"))
        return Response(ok(data))
    except Exception as e:  # noqa
        return Response(fail(str(e)))


@api_view(["GET"])
def benchmark_platforms(request):
    try:
        return Response(ok(services.benchmark_platforms()))
    except Exception as e:  # noqa
        return Response(fail(str(e)))


@api_view(["GET"])
def benchmark_search(request):
    try:
        data = services.benchmark_search(
            q=request.GET.get("q", ""),
            platform=request.GET.get("platform", "ALL"),
            sort=request.GET.get("sort", "fans"),
            fan_level=request.GET.get("fan_level", ""),
        )
        return Response(ok(data))
    except Exception as e:  # noqa
        return Response(fail(str(e)))


@api_view(["GET"])
def yunzhangfang_overview(request):
    try:
        return Response(ok(services.yunzhangfang_overview()))
    except Exception as e:  # noqa
        return Response(fail(str(e)))


@api_view(["GET", "POST"])
def training_video_list(request):
    try:
        if request.method == "POST":
            return Response(ok(services.create_training_video(dict(request.data))))
        return Response(ok(services.list_training_videos()))
    except Exception as e:  # noqa
        return Response(fail(str(e)))


@api_view(["PATCH", "DELETE"])
def training_video_detail(request, pk):
    try:
        if request.method == "DELETE":
            services.delete_training_video(pk)
            return Response(ok(None, "已删除"))
        v = services.update_training_video(pk, dict(request.data))
        if not v:
            return Response(fail("未找到该视频"))
        return Response(ok(v))
    except Exception as e:  # noqa
        return Response(fail(str(e)))


# ---------------- 钉钉通讯录同步（2026-10-28 增量，仅老板/人事可用） ----------------
from django.conf import settings as dj_settings  # noqa: E402


def _is_hr_boss(user):
    return bool(user and user.is_authenticated and
                (user.is_superuser or getattr(user, "role", None) in ("BOSS", "HR")))


@api_view(["GET"])
def dingtalk_status(request):
    """钉钉集成状态（是否已配置凭证）"""
    from . import dingtalk
    if not _is_hr_boss(request.user):
        return Response(fail("仅老板/人事可查看钉钉集成状态"), status=403)
    return Response(ok({
        "configured": dingtalk.is_configured(),
        "app_key_masked": (dj_settings.DINGTALK.get("APP_KEY") or "")[:6] + "****"
        if dj_settings.DINGTALK.get("APP_KEY") else "",
    }))


@api_view(["POST"])
def dingtalk_sync(request):
    """一键同步钉钉通讯录（部门 + 成员 → 系统组织架构）

    入参：{"dry_run": true} 时只预演统计不写库。
    """
    from . import dingtalk
    if not _is_hr_boss(request.user):
        return Response(fail("仅老板/人事可执行钉钉同步"), status=403)
    try:
        stats = dingtalk.sync_org(dry_run=bool(request.data.get("dry_run")))
        return Response(ok(stats))
    except Exception as e:  # noqa
        return Response(fail(str(e)))
