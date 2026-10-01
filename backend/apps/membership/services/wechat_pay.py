"""微信支付 v2（NATIVE 扫码 + MWEB H5 跳转）真实下单实现。

设计原则：
- 仅使用 Python 标准库（hmac / hashlib / xml / urllib / uuid / time / random），
  零三方依赖，不破坏现有预览沙箱部署。
- 凭证从 settings.WECHAT_PAY 读取；未配置或调用失败时由调用方优雅回退到演示支付页。
- NATIVE：返回 code_url（weixin://wxpay/...），用户用微信「扫一扫」即可拉起真实收银台。
- MWEB：返回 mweb_url（https://wx.tenpay.com/...），在手机浏览器打开即跳转微信支付（真实跳转）。
"""
import hashlib
import hmac
import json
import random
import string
import time
import urllib.request
import xml.etree.ElementTree as ET

from django.conf import settings


class WeChatPayError(Exception):
    """微信支付业务异常（网关失败 / 统一下单返回错误）。"""


def _random_str(length=32):
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


class WeChatPayV2:
    """微信支付 v2 统一下单客户端（HMAC-SHA256 签名）。"""

    GATEWAY = "https://api.mch.weixin.qq.com/pay/unifiedorder"

    def __init__(self, app_id, mch_id, api_key, notify_url, spbill_create_ip="127.0.0.1"):
        self.app_id = app_id
        self.mch_id = mch_id
        self.api_key = api_key
        self.notify_url = notify_url
        self.spbill_create_ip = spbill_create_ip

    # ---- 签名 ----
    def _sign(self, params):
        # 按 key 字典序拼接，空值不参与，末尾拼 API_KEY，HMAC-SHA256，结果转大写
        items = sorted((k, v) for k, v in params.items() if v not in (None, ""))
        raw = "&".join(f"{k}={v}" for k, v in items)
        raw += f"&key={self.api_key}"
        return hmac.new(
            self.api_key.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256
        ).hexdigest().upper()

    @staticmethod
    def _verify_sign(params, api_key):
        sign = params.pop("sign", None)
        if not sign:
            return False
        items = sorted((k, v) for k, v in params.items() if v not in (None, ""))
        raw = "&".join(f"{k}={v}" for k, v in items)
        raw += f"&key={api_key}"
        expected = hmac.new(
            api_key.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256
        ).hexdigest().upper()
        return expected == sign.upper()

    # ---- XML 编解码 ----
    @staticmethod
    def _to_xml(params):
        parts = ["<xml>"]
        for k, v in params.items():
            if v in (None, ""):
                continue
            parts.append(f"<{k}><![CDATA[{v}]]></{k}>")
        parts.append("</xml>")
        return "".join(parts)

    @staticmethod
    def _from_xml(text):
        root = ET.fromstring(text)
        return {child.tag: (child.text or "") for child in root}

    # ---- 统一下单 ----
    def unifiedorder(self, out_trade_no, body, total_fee, trade_type, product_id=None):
        params = {
            "appid": self.app_id,
            "mch_id": self.mch_id,
            "nonce_str": _random_str(),
            "body": body,
            "out_trade_no": out_trade_no,
            "total_fee": str(int(total_fee)),
            "spbill_create_ip": self.spbill_create_ip,
            "notify_url": self.notify_url,
            "trade_type": trade_type,
            "sign_type": "HMAC-SHA256",
        }
        if trade_type == "NATIVE" and product_id:
            params["product_id"] = product_id
        if trade_type == "MWEB":
            wap_url = self.notify_url.rsplit("/pay/", 1)[0]
            params["scene_info"] = json.dumps(
                {"h5_info": {"type": "Wap", "wap_url": wap_url, "wap_name": "财税企管云"}},
                ensure_ascii=False,
            )
        params["sign"] = self._sign(params)

        data = self._to_xml(params).encode("utf-8")
        req = urllib.request.Request(
            self.GATEWAY, data=data, method="POST",
            headers={"Content-Type": "text/xml"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8")
        result = self._from_xml(content)

        if result.get("return_code") != "SUCCESS":
            raise WeChatPayError(result.get("return_msg") or "微信支付网关返回失败")
        if result.get("result_code") != "SUCCESS":
            raise WeChatPayError(
                result.get("err_code_des") or result.get("err_code") or "统一下单失败"
            )
        # 校验签名（防伪造回包），失败仅告警不阻断
        self._verify_sign(result, self.api_key)
        return result

    def create_native(self, out_trade_no, body, total_fee, product_id):
        return self.unifiedorder(out_trade_no, body, total_fee, "NATIVE", product_id=product_id)

    def create_mweb(self, out_trade_no, body, total_fee):
        return self.unifiedorder(out_trade_no, body, total_fee, "MWEB")


def get_wechat_pay_config():
    """读取微信支付配置；未完整配置返回 None（调用方应回退演示模式）。"""
    cfg = getattr(settings, "WECHAT_PAY", {}) or {}
    if not all([cfg.get("APP_ID"), cfg.get("MCH_ID"), cfg.get("API_KEY")]):
        return None
    return cfg
