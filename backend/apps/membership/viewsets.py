"""会员体系视图集"""
import re
import time
import xml.etree.ElementTree as ET

from django.conf import settings
from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action, api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.viewsets import ScopeModelViewSet
from .models import MembershipPlan, Subscription
from .serializers import MembershipPlanSerializer, SubscriptionSerializer
from .services.wechat_pay import WeChatPayV2, WeChatPayError, get_wechat_pay_config


class PlanViewSet(viewsets.ModelViewSet):
    """套餐：列表/增删改（创建人记录到 created_by）"""
    queryset = MembershipPlan.objects.filter(is_deleted=False)
    serializer_class = MembershipPlanSerializer

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()

    def perform_update(self, serializer):
        serializer.save()


class SubscriptionViewSet(ScopeModelViewSet):
    """订阅：按创建人收窄；管理员可见全部"""
    owner_field = "created_by"
    queryset = Subscription.objects.filter(is_deleted=False)
    serializer_class = SubscriptionSerializer

    @action(detail=False, methods=["get"])
    def my(self, request):
        """当前用户最近一条订阅（演示视角）"""
        qs = self.get_queryset().filter(created_by=request.user).order_by("-created_at")
        obj = qs.first()
        return Response(SubscriptionSerializer(obj).data if obj else None)

    @action(detail=True, methods=["post"])
    def status(self, request, pk=None):
        """修改订阅状态：body={status}"""
        obj = self.get_object()
        new_status = request.data.get("status")
        if new_status in dict(Subscription.STATUS):
            obj.status = new_status
            obj.save(update_fields=["status"])
        return Response(SubscriptionSerializer(obj).data)


@api_view(["GET"])
def permissions_view(request):
    """返回当前用户所属会员等级允许的功能权限 key 列表"""
    sub = (
        Subscription.objects.filter(created_by=request.user, status="ACTIVE", is_deleted=False)
        .order_by("-plan__level")
        .first()
    )
    if sub:
        level = sub.plan.code
        perms = sub.plan.permissions or []
    else:
        level = "FREE"
        perms = ["dashboard", "onboarding"]
    return Response({"level": level, "permissions": perms})


class PayView(APIView):
    """统一下单入口：返回真实可收款的微信支付参数，或回退到演示支付页。

    请求体：{ "subscription_id": <int>, "method": "WECHAT" | "ALIPAY" | "BANK" }
    返回：
      - 真实模式（已配置商户凭证）：{ mode:"real", code_url, mweb_url, out_trade_no, amount }
      - 演示模式（未配置/调用失败）：{ mode:"demo", pay_url, reason }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        sub_id = request.data.get("subscription_id") or request.data.get("subscription")
        method = (request.data.get("method") or (request.data.get("pay_method") or "")).upper()
        try:
            sub = Subscription.objects.get(pk=sub_id, is_deleted=False)
        except (Subscription.DoesNotExist, ValueError, TypeError):
            return Response({"detail": "订单不存在"}, status=404)

        # 金额：优先实付金额，否则取套餐月价；微信不允许 0 元下单
        amount = sub.amount or (sub.plan.price_monthly if sub.plan else 0)
        try:
            total_fee = int(float(amount) * 100)
        except (TypeError, ValueError):
            total_fee = 0
        if total_fee <= 0:
            total_fee = 1

        body = f"财税企管云-{sub.plan.name if sub.plan else '会员'}"
        # 优先使用配置的公网基址，避免沙箱内部代理 Host 导致回调/回跳地址不可达
        origin = getattr(settings, "SITE_BASE_URL", "") or request.build_absolute_uri("/").rstrip("/")
        demo_pay_url = (
            f"{origin}/membership/pay?order={sub.id}"
            f"&m={method or sub.pay_method}&amount={total_fee / 100}"
        )

        # 支付宝 / 对公转账：当前为演示模式（真实收款需 RSA 签名库，沙箱未预装）
        if method != "WECHAT":
            return Response({
                "mode": "demo", "pay_url": demo_pay_url,
                "reason": "支付宝/对公转账暂为演示模式",
            })

        cfg = get_wechat_pay_config()
        if not cfg:
            return Response({
                "mode": "demo", "pay_url": demo_pay_url,
                "reason": "未配置微信支付商户凭证，已回退演示支付页",
            })

        try:
            client = WeChatPayV2(
                app_id=cfg["APP_ID"], mch_id=cfg["MCH_ID"], api_key=cfg["API_KEY"],
                notify_url=f"{origin}/api/membership/pay/notify/",
                spbill_create_ip=request.META.get("REMOTE_ADDR", "127.0.0.1"),
            )
            ts = int(time.time())
            native = client.create_native(f"FP{sub.id}N{ts}", body, total_fee, product_id=str(sub.id))
            mweb = client.create_mweb(f"FP{sub.id}M{ts}", body, total_fee)
            return Response({
                "mode": "real",
                "code_url": native.get("code_url", ""),
                "mweb_url": mweb.get("mweb_url", ""),
                "out_trade_no": f"FP{sub.id}M{ts}",
                "pay_url": demo_pay_url,
                "amount": total_fee / 100,
            })
        except WeChatPayError as e:
            return Response({"mode": "demo", "pay_url": demo_pay_url, "reason": f"微信支付调用失败：{e}"})
        except Exception as e:  # 网络/超时等不可预期错误，绝不阻断前端流程
            return Response({"mode": "demo", "pay_url": demo_pay_url, "reason": f"微信支付暂不可用：{e}"})


def pay_notify(request):
    """微信支付异步通知（服务器到服务器，无需鉴权）。

    微信以 text/xml 形式 POST 支付结果；校验结果后把对应订阅标记为已开通，
    并返回 <return_code>SUCCESS</return_code> 告知微信已收到（否则微信会持续重试）。
    """
    if request.method != "POST":
        return HttpResponse(
            "<xml><return_code><![CDATA[FAIL]]></return_code></xml>", content_type="text/xml"
        )
    try:
        root = ET.fromstring(request.body.decode("utf-8"))
        data = {child.tag: (child.text or "") for child in root}
    except Exception:
        return HttpResponse(
            "<xml><return_code><![CDATA[FAIL]]></return_code></xml>", content_type="text/xml"
        )

    if data.get("return_code") == "SUCCESS" and data.get("result_code") == "SUCCESS":
        m = re.search(r"FP(\d+)", data.get("out_trade_no", ""))
        if m:
            try:
                sub = Subscription.objects.get(pk=int(m.group(1)), is_deleted=False)
                if sub.status != "ACTIVE":
                    sub.status = "ACTIVE"
                    sub.save(update_fields=["status"])
            except Subscription.DoesNotExist:
                pass

    return HttpResponse(
        "<xml><return_code><![CDATA[SUCCESS]]></return_code></xml>", content_type="text/xml"
    )
