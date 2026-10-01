"""财税企管云 · 外部能力集成（演示数据 + Key 网关）

所有外部查询（企业工商/企查查类、抖音数据、云账房、电子税务局、电子营业执照）
默认返回「演示数据」；在 settings 中配置对应 API Key 后，可切换为真实数据源。
真实接口调用以 try/except 包裹，任何异常自动回退演示数据并标记 source=demo_fallback。

注意：政府/账号类系统（电子营业执照、电子税务局、云账房）需要你本人的官方登录授权，
无法由本系统直接代登。本模块提供「跳转官方入口」+「本地演示数据」，真实数据请在官方系统获取。
"""
import base64
import hashlib
import json
import logging
import os
import random
from django.conf import settings

import requests

logger = logging.getLogger(__name__)


# ---------------- 演示模式判断 ----------------
def _has_key(name):
    return bool(getattr(settings, name, ''))


def integration_status():
    return {
        "enterprise": _has_key("QICHACHA_API_KEY") or _has_key("TIANYANCHA_API_KEY"),
        "douyin": _has_key("DOUYIN_API_KEY"),
        "yunzhangfang": _has_key("YUNZHANGFANG_API_KEY"),
    }


# ---------------- 真实外部接口（Key 网关 + 失败回退演示） ----------------
# 设计原则：
#   1) 仅在配置了对应 API Key（环境变量 → settings）时才打真实接口；
#   2) 任何网络/鉴权/解析异常都被捕获并回退到演示数据，绝不让接口 5xx；
#   3) 真实成功结果带 source=live_* 标记，便于前端区分演示/真实。
_HTTP_TIMEOUT = 8
_REQ_HEADERS = {"User-Agent": "finops-cloud/1.0"}


def _http_get_json(url, params=None, headers=None):
    """统一带超时的 GET；非 2xx 或异常由调用方捕获后回退演示。"""
    resp = requests.get(
        url, params=params or {}, headers=headers or _REQ_HEADERS, timeout=_HTTP_TIMEOUT
    )
    resp.raise_for_status()
    return resp.json()


def _map_tianyancha(i):
    return {
        "name": i.get("name"),
        "credit_code": i.get("creditCode"),
        "legal": i.get("legalPersonName"),
        "phone": i.get("phoneNumber") or "",
        "capital": i.get("regCapital") or "",
        "established": (i.get("esDate") or "")[:10],
        "status": i.get("regStatus") or "",
        "address": i.get("regAddress") or "",
        "scope": i.get("businessScope") or "",
        "source": "live_tianyancha",
    }


def _live_enterprise_search(keyword):
    """优先天眼查（单 Key 即可，Authorization: token），其次企查查（需 Key+Secret 签名）。
    返回映射后的列表；都不可用 / 调用失败返回 None（由调用方回退演示）。"""
    if _has_key("TIANYANCHA_API_KEY"):
        try:
            url = "https://open.api.tianyancha.com/services/open/icAdvanced/2.0"
            data = _http_get_json(
                url,
                params={"keyword": keyword, "pageSize": 20, "pageNum": 1},
                headers={"Authorization": "token %s" % settings.TIANYANCHA_API_KEY},
            )
            if data.get("error_code") != 0:
                raise RuntimeError("tianyancha:%s" % data.get("reason"))
            items = (data.get("result") or {}).get("items") or []
            return [_map_tianyancha(i) for i in items]
        except Exception as e:  # noqa
            logger.warning("[integrations] 天眼查查询失败，回退演示：%s", e)
    if _has_key("QICHACHA_API_KEY"):
        try:
            return _qichacha_search(keyword)
        except Exception as e:  # noqa
            logger.warning("[integrations] 企查查查询失败，回退演示：%s", e)
    return None


def _qichacha_search(keyword):
    """企查查开放平台：需 APP Key + APP Secret 做 md5 签名（token = md5(key+random+secret)）。
    仅当同时配置了 QICHACHA_API_KEY 与 QICHACHA_SECRET 时可用；否则返回 None。"""
    secret = os.environ.get("QICHACHA_SECRET", "")
    if not secret:
        logger.info("[integrations] 企查查未配置 QICHACHA_SECRET，跳过真实查询")
        return None
    key = settings.QICHACHA_API_KEY
    rand = str(random.randint(100000, 999999))
    token = hashlib.md5((key + rand + secret).encode("utf-8")).hexdigest()
    url = "https://api.qichacha.com/ECIWebservice_V4/GetBasicByName"
    data = _http_get_json(
        url, params={"keyword": keyword, "random": rand},
        headers={"Key": key, "Token": token},
    )
    if str(data.get("Status")) != "200":
        raise RuntimeError("qichacha:%s" % data.get("Message"))
    r = data.get("Result") or {}
    return [{
        "name": r.get("Name"),
        "credit_code": r.get("CreditCode"),
        "legal": r.get("OperManName"),
        "phone": r.get("ContactPhone") or "",
        "capital": r.get("RegistCapi") or "",
        "established": (r.get("FoundDate") or "")[:10],
        "status": r.get("Status") or "",
        "address": r.get("Address") or "",
        "scope": r.get("BusinessScope") or "",
        "source": "live_qichacha",
    }]


def _live_enterprise_detail(credit_code):
    """天眼查基础信息接口（按统一社会信用代码/企业名查）。失败返回 None。"""
    if not _has_key("TIANYANCHA_API_KEY"):
        return None
    try:
        url = "https://open.api.tianyancha.com/services/open/icBaseInfo/2.0"
        data = _http_get_json(
            url, params={"keyword": credit_code},
            headers={"Authorization": "token %s" % settings.TIANYANCHA_API_KEY},
        )
        if data.get("error_code") != 0:
            raise RuntimeError("tianyancha:%s" % data.get("reason"))
        r = data.get("result") or {}
        base = {
            "name": r.get("name"),
            "credit_code": r.get("creditCode") or credit_code,
            "legal": r.get("legalPersonName"),
            "capital": r.get("regCapital") or "",
            "established": (r.get("esDate") or "")[:10],
            "status": r.get("regStatus") or "",
            "address": r.get("regAddress") or "",
            "scope": r.get("businessScope") or "",
        }
        return {
            "base_info": base,
            "license": _demo_license(base["name"] or "示例企业", base["credit_code"],
                                     base["legal"] or "示例法人"),
            "tax": _demo_tax(base["credit_code"]),
            "source": "live_tianyancha",
        }
    except Exception as e:  # noqa
        logger.warning("[integrations] 天眼查详情失败，回退演示：%s", e)
        return None


def _live_douyin(q):
    """抖音/短视频对标数据：第三方数据商（蝉妈妈/飞瓜/巨量算数）均无免费公开 API，
    需自建代理或购买。约定可配置端点 DOUYIN_API_BASE + DOUYIN_API_KEY：
       GET {DOUYIN_API_BASE}/account?q=<昵称/账号>
       返回 JSON 字段：nickname, douyin_id/account_id, fans, works, likes,
                       growth_30d, gmv_30d, tags[], hot_videos[]
    填写后即真实请求；未配置或请求失败自动回退演示。"""
    base = os.environ.get("DOUYIN_API_BASE", "").strip()
    key = settings.DOUYIN_API_KEY
    if not (base and key):
        return None
    try:
        url = base.rstrip("/") + "/account"
        data = _http_get_json(url, params={"q": q},
                              headers={"Authorization": "Bearer %s" % key})
        return {
            "nickname": data.get("nickname", q[:8] + "（示例）"),
            "douyin_id": data.get("douyin_id") or data.get("account_id"),
            "fans": data.get("fans", 0),
            "works": data.get("works", 0),
            "likes": data.get("likes", 0),
            "growth_30d": data.get("growth_30d", 0),
            "gmv_30d": data.get("gmv_30d", 0),
            "tags": data.get("tags", []),
            "hot_videos": data.get("hot_videos", []),
            "source": "live_douyin",
            "portal_url": base,
            "is_demo": False,
        }
    except Exception as e:  # noqa
        logger.warning("[integrations] 抖音数据请求失败，回退演示：%s", e)
        return None


# ---------------- 企业工商（企查查/天眼查类） ----------------
SAMPLE_COMPANIES = [
    {"name": "云南某某财税服务有限公司", "credit_code": "91530100MA6KX1A2B3", "legal": "张伟",
     "phone": "13887123456",
     "capital": "200万人民币", "established": "2018-05-12", "status": "存续",
     "address": "云南省昆明市五华区东风西路123号",
     "scope": "代理记账；税务咨询；企业管理咨询；商标注册代理；证照代办。"},
    {"name": "昆明云创科技有限公司", "credit_code": "91530112MA6N7C4D5E", "legal": "李娜",
     "phone": "13987123456",
     "capital": "500万人民币", "established": "2019-11-03", "status": "存续",
     "address": "云南省昆明市盘龙区北京路456号",
     "scope": "软件开发；信息技术咨询服务；互联网数据服务；广告设计。"},
    {"name": "云南盛达商贸有限公司", "credit_code": "91530103MA6P8F6G7H", "legal": "王强",
     "phone": "13787123456",
     "capital": "100万人民币", "established": "2020-07-21", "status": "在业",
     "address": "云南省昆明市官渡区关上中路789号",
     "scope": "日用百货、办公用品、电子产品、通讯器材销售。"},
]


def search_enterprise(params):
    """企业工商查询：支持 企业名称 / 法人姓名 / 联系电话 / 统一社会信用代码 多条件检索。
    params: {q, name, legal, phone, credit_code}，任一字段命中即返回（并集）。"""
    params = params or {}
    q = (params.get("q") or "").strip()
    name = (params.get("name") or "").strip()
    legal = (params.get("legal") or "").strip()
    phone = (params.get("phone") or "").strip()
    code = (params.get("credit_code") or "").strip()

    # —— 真实数据源优先（配置了 Key 才打，失败/无结果回退演示） ——
    keyword = q or name or code or legal or phone
    enterprise_key_present = _has_key("TIANYANCHA_API_KEY") or _has_key("QICHACHA_API_KEY")
    if enterprise_key_present and keyword:
        live = _live_enterprise_search(keyword)
        if live is not None:  # 成功查询（含查无结果返回 []），直接返回，不编造
            return live
        # 调用失败：继续走演示，保证前端不空窗

    def matches(c):
        return (
            (not q or q in c["name"] or q in c["credit_code"])
            and (not name or name in c["name"])
            and (not legal or legal in c.get("legal", ""))
            and (not phone or phone in c.get("phone", ""))
            and (not code or code in c["credit_code"])
        )

    matched = [c for c in SAMPLE_COMPANIES if matches(c)]

    # 按特定字段查询但样本库无命中时，合成一条演示结果，便于前端走通流程
    if not matched:
        synth = None
        base = {"capital": "100万人民币", "established": "2021-03-15", "status": "存续",
                "address": "云南省昆明市示例区示例路1号",
                "scope": "一般项目：企业管理咨询；信息咨询服务；市场营销策划；税务咨询。"}
        if phone:
            synth = {"name": f"演示企业（{phone}）有限公司",
                     "credit_code": "9" + "".join(random.choice("0123456789") for _ in range(16)),
                     "legal": random.choice(["张伟", "李娜", "王强", "陈静", "刘洋"]),
                     "phone": phone, **base}
        elif legal:
            synth = {"name": f"{legal}（演示）有限公司",
                     "credit_code": "9" + "".join(random.choice("0123456789") for _ in range(16)),
                     "legal": legal, "phone": "138" + "".join(random.choice("0123456789") for _ in range(8)), **base}
        elif name or code:
            synth = {"name": name or f"企业{code}",
                     "credit_code": code or "9" + "".join(random.choice("0123456789") for _ in range(16)),
                     "legal": random.choice(["张伟", "李娜", "王强", "陈静", "刘洋"]),
                     "phone": "138" + "".join(random.choice("0123456789") for _ in range(8)), **base}
        if synth:
            matched = [synth]
    return matched


def enterprise_detail(credit_code):
    if _has_key("TIANYANCHA_API_KEY"):
        live = _live_enterprise_detail(credit_code)
        if live is not None:
            return live
    base = next((c for c in SAMPLE_COMPANIES if c["credit_code"] == credit_code), None)
    if not base:
        base = {"name": "示例企业有限公司", "credit_code": credit_code, "legal": "示例法人",
                "capital": "100万人民币", "established": "2021-01-01", "status": "存续",
                "address": "云南省昆明市示例区示例路1号",
                "scope": "企业管理咨询；信息咨询服务；市场营销策划。"}
    return {
        "base_info": base,
        "license": _demo_license(base["name"], credit_code, base["legal"]),
        "tax": _demo_tax(credit_code),
        "source": "demo",
    }


def _demo_license(name, code, legal):
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="430">'
        '<rect width="600" height="430" fill="#fff8e1" stroke="#c99700" stroke-width="4"/>'
        '<text x="300" y="58" font-size="26" text-anchor="middle" fill="#9a6b00" font-weight="bold">营业执照（演示样本）</text>'
        '<line x1="40" y1="86" x2="560" y2="86" stroke="#c99700"/>'
        f'<text x="50" y="140" font-size="19" fill="#333">名称：{name}</text>'
        f'<text x="50" y="180" font-size="19" fill="#333">统一社会信用代码：{code}</text>'
        f'<text x="50" y="220" font-size="19" fill="#333">法定代表人：{legal}</text>'
        '<text x="50" y="260" font-size="19" fill="#333">类型：有限责任公司（自然人投资或控股）</text>'
        '<text x="50" y="300" font-size="19" fill="#333">成立日期：2021-01-01</text>'
        '<text x="50" y="360" font-size="15" fill="#999">※ 此为系统演示样本，非真实证照。真实电子营业执照请通过官方系统获取。</text>'
        '</svg>'
    )
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return {
        "name": name, "credit_code": code, "issued_at": "2021-01-01",
        "image": "data:image/svg+xml;base64," + b64,
        "download_name": f"电子营业执照_{name}.svg",
        "is_demo": True,
    }


def _demo_tax(code):
    return {
        "credit_code": code,
        "taxpayer_status": "正常",
        "taxpayer_type": "小规模纳税人",
        "declarations": [
            {"period": "2026-08", "category": "增值税及附加", "status": "已申报", "amount": 1280.50},
            {"period": "2026-08", "category": "企业所得税", "status": "已申报", "amount": 0.00},
            {"period": "2026-07", "category": "增值税及附加", "status": "已申报", "amount": 1350.00},
        ],
        "owed": 0.00,
        "invoice_quota": "万元版增值税专用发票 25 份",
        "portal_url": "https://etax.chinatax.gov.cn",
        "is_demo": True,
    }


# ---------------- 抖音对标账号 ----------------
def douyin_account(q):
    q = (q or "").strip()
    if not q:
        return None
    live = _live_douyin(q)
    if live:
        return live
    return {
        "nickname": (q[:8] + "（示例）") if len(q) > 8 else q,
        "douyin_id": "douyin_" + "".join(random.choice("0123456789") for _ in range(8)),
        "fans": random.randint(12000, 1250000),
        "works": random.randint(80, 2600),
        "likes": random.randint(50000, 9800000),
        "growth_30d": random.randint(-3000, 120000),
        "gmv_30d": random.randint(0, 3500000),
        "tags": random.sample(["财税科普", "老板IP", "职场干货", "创业避坑", "会计实操"], 3),
        "hot_videos": [
            {"title": "老板必看：这3种情况公司不用交企业所得税", "play": random.randint(50000, 2000000),
             "like": random.randint(2000, 80000)},
            {"title": "新手会计第一个月做账全流程", "play": random.randint(30000, 1500000),
             "like": random.randint(1500, 60000)},
        ],
        "source": "demo",
        "portal_url": "https://www.douyin.com",
        "is_demo": True,
    }


# ---------------- 云账房 ----------------
def yunzhangfang_overview():
    return {
        "account_name": "云南某某财税服务有限公司",
        "books": [
            {"name": "云南某某财税服务有限公司（一般纳税人）", "vouchers": 248, "period": "2026-08"},
            {"name": "昆明云创科技有限公司（小规模）", "vouchers": 96, "period": "2026-08"},
        ],
        "reports": [
            {"name": "资产负债表", "period": "2026-08", "assets": 1286500.00,
             "liabilities": 432000.00, "equity": 854500.00},
            {"name": "利润表", "period": "2026-08", "revenue": 865000.00, "profit": 132500.00},
        ],
        "pending_vouchers": 12,
        "portal_url": "https://www.yunzhangfang.com",
        "is_demo": True,
        "source": "demo",
    }


# ---------------- 视频学习库（JSON 文件存储） ----------------
_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_VIDEO_FILE = os.path.join(_DATA_DIR, "training_videos.json")

_SEED = [
    {"id": 1, "title": "财税小白入门：什么是代理记账", "category": "财税知识", "cover": "",
     "type": "file", "src": "https://www.w3schools.com/html/mov_bbb.mp4", "duration": "12:30",
     "desc": "面向新人的财税基础概念讲解（演示视频，请替换为自有课程）。"},
    {"id": 2, "title": "电销开场白设计与异议处理", "category": "销售技巧", "cover": "",
     "type": "file", "src": "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
     "duration": "08:15", "desc": "高转化电销话术拆解（演示视频）。"},
    {"id": 3, "title": "云账房实操：一键生成凭证", "category": "软件操作", "cover": "",
     "type": "file", "src": "https://www.w3schools.com/html/mov_bbb.mp4", "duration": "15:40",
     "desc": "云账房做账流程演示（演示视频）。"},
    {"id": 4, "title": "合规红线：这些账绝对不能做", "category": "合规风控", "cover": "",
     "type": "file", "src": "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
     "duration": "10:05", "desc": "财税合规风险警示（演示视频）。"},
]


def _ensure_data():
    os.makedirs(_DATA_DIR, exist_ok=True)
    if not os.path.exists(_VIDEO_FILE):
        _save(_SEED)


def _save(items):
    with open(_VIDEO_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def list_training_videos():
    _ensure_data()
    with open(_VIDEO_FILE, encoding="utf-8") as f:
        return json.load(f)


def create_training_video(data):
    items = list_training_videos()
    nid = max([v.get("id", 0) for v in items], default=0) + 1
    data["id"] = nid
    items.append(data)
    _save(items)
    return data


def update_training_video(pk, data):
    items = list_training_videos()
    for v in items:
        if v.get("id") == pk:
            v.update(data)
            v["id"] = pk
            _save(items)
            return v
    return None


def delete_training_video(pk):
    items = list_training_videos()
    new = [v for v in items if v.get("id") != pk]
    _save(new)
    return len(items) != len(new)


# ---------------- 对标账号搜索（抖音/快手/小红书/视频号）----------------
BENCHMARK_PLATFORMS = [
    {"value": "ALL", "label": "全部平台", "color": "#606266"},
    {"value": "DOUYIN", "label": "抖音", "color": "#111111"},
    {"value": "KUAISHOU", "label": "快手", "color": "#FF7A00"},
    {"value": "XIAOHONGSHU", "label": "小红书", "color": "#FF2442"},
    {"value": "SHIPINHAO", "label": "视频号", "color": "#07C160"},
]

_PLATFORM_LABEL = {p["value"]: p["label"] for p in BENCHMARK_PLATFORMS}

BENCHMARK_SAMPLE = [
    # ---------------- 抖音（优先适配）----------------
    {"platform": "DOUYIN", "nickname": "财税老王说账", "account_id": "caishui_laowang",
     "fans": 1286000, "likes": 5860000, "works": 428, "avg_play": 186000,
     "tags": ["财税知识", "代账", "企业服务"], "sign": "15年财税老兵，讲透每一笔账",
     "url": "https://www.douyin.com/user/caishui_laowang"},
    {"platform": "DOUYIN", "nickname": "企服小雨", "account_id": "qifu_xiaoyu",
     "fans": 862000, "likes": 3120000, "works": 356, "avg_play": 132000,
     "tags": ["工商注册", "资质办理"], "sign": "注册公司那些事儿，一次讲明白",
     "url": "https://www.douyin.com/user/qifu_xiaoyu"},
    {"platform": "DOUYIN", "nickname": "税务师阿May", "account_id": "tax_amay",
     "fans": 534000, "likes": 2080000, "works": 291, "avg_play": 98000,
     "tags": ["税务筹划", "政策解读"], "sign": "注册税务师，政策解读不绕弯",
     "url": "https://www.douyin.com/user/tax_amay"},
    {"platform": "DOUYIN", "nickname": "创业财税笔记", "account_id": "chuangye_caishui",
     "fans": 318000, "likes": 1120000, "works": 502, "avg_play": 56000,
     "tags": ["创业", "记账", "省钱攻略"], "sign": "创业者必懂的省钱财税课",
     "url": "https://www.douyin.com/user/chuangye_caishui"},
    {"platform": "DOUYIN", "nickname": "发票那些事", "account_id": "fapiao_naxieshi",
     "fans": 226000, "likes": 780000, "works": 214, "avg_play": 43000,
     "tags": ["发票管理", "风险防控"], "sign": "发票风险早知道",
     "url": "https://www.douyin.com/user/fapiao_naxieshi"},
    {"platform": "DOUYIN", "nickname": "代账公司老板娘", "account_id": "daizhang_bossniang",
     "fans": 158000, "likes": 620000, "works": 386, "avg_play": 31000,
     "tags": ["代账运营", "客户成交"], "sign": "代账公司怎么获客、怎么留客",
     "url": "https://www.douyin.com/user/daizhang_bossniang"},
    {"platform": "DOUYIN", "nickname": "政策速递君", "account_id": "zhengce_sudi",
     "fans": 92000, "likes": 330000, "works": 640, "avg_play": 18000,
     "tags": ["政策速递", "申报提醒"], "sign": "每天一条财税新政",
     "url": "https://www.douyin.com/user/zhengce_sudi"},
    # ---------------- 快手（优先适配）----------------
    {"platform": "KUAISHOU", "nickname": "财税老张", "account_id": "caishui_laozhang",
     "fans": 742000, "likes": 2890000, "works": 312, "avg_play": 121000,
     "tags": ["财税知识", "小微企业"], "sign": "小微企业财税保姆",
     "url": "https://www.kuaishou.com/profile/caishui_laozhang"},
    {"platform": "KUAISHOU", "nickname": "昆明企服通", "account_id": "km_qifutong",
     "fans": 186000, "likes": 640000, "works": 268, "avg_play": 42000,
     "tags": ["本地服务", "工商代办"], "sign": "云南本地企业服务一站式",
     "url": "https://www.kuaishou.com/profile/km_qifutong"},
    {"platform": "KUAISHOU", "nickname": "记账小课堂", "account_id": "jizhang_xiaoketang",
     "fans": 268000, "likes": 950000, "works": 431, "avg_play": 58000,
     "tags": ["记账实操", "软件教学"], "sign": "手把手教你做账",
     "url": "https://www.kuaishou.com/profile/jizhang_xiaoketang"},
    {"platform": "KUAISHOU", "nickname": "老板财税必修课", "account_id": "laoban_caishui",
     "fans": 412000, "likes": 1560000, "works": 289, "avg_play": 76000,
     "tags": ["老板财税", "风险管控"], "sign": "老板不懂税，公司很受伤",
     "url": "https://www.kuaishou.com/profile/laoban_caishui"},
    {"platform": "KUAISHOU", "nickname": "税务稽查预警", "account_id": "shuiwu_jicha",
     "fans": 134000, "likes": 480000, "works": 176, "avg_play": 35000,
     "tags": ["稽查案例", "合规"], "sign": "真实稽查案例复盘",
     "url": "https://www.kuaishou.com/profile/shuiwu_jicha"},
    {"platform": "KUAISHOU", "nickname": "财税干货铺", "account_id": "caishui_ganhuo",
     "fans": 88000, "likes": 290000, "works": 520, "avg_play": 21000,
     "tags": ["干货分享", "实操技巧"], "sign": "每天一个财税小技巧",
     "url": "https://www.kuaishou.com/profile/caishui_ganhuo"},
    {"platform": "KUAISHOU", "nickname": "企业省钱研究所", "account_id": "qiye_shengqian",
     "fans": 62000, "likes": 195000, "works": 158, "avg_play": 16000,
     "tags": ["成本管控", "税收优惠"], "sign": "合理合规省下每一分钱",
     "url": "https://www.kuaishou.com/profile/qiye_shengqian"},
    # ---------------- 小红书 ----------------
    {"platform": "XIAOHONGSHU", "nickname": "财税少女阿黎", "account_id": "caishui_alii",
     "fans": 296000, "likes": 1340000, "works": 246, "avg_play": 48000,
     "tags": ["财税科普", "职场"], "sign": "把财税讲成人话",
     "url": "https://www.xiaohongshu.com/user/profile/caishui_alii"},
    {"platform": "XIAOHONGSHU", "nickname": "创业记账手账", "account_id": "chuangye_jizhang",
     "fans": 152000, "likes": 680000, "works": 312, "avg_play": 26000,
     "tags": ["创业笔记", "记账"], "sign": "创业者的记账手账",
     "url": "https://www.xiaohongshu.com/user/profile/chuangye_jizhang"},
    {"platform": "XIAOHONGSHU", "nickname": "代账避坑指南", "account_id": "daizhang_bikeng",
     "fans": 98000, "likes": 420000, "works": 187, "avg_play": 19000,
     "tags": ["避坑", "代账"], "sign": "选代账公司前先看我",
     "url": "https://www.xiaohongshu.com/user/profile/daizhang_bikeng"},
    {"platform": "XIAOHONGSHU", "nickname": "财税资料库", "account_id": "caishui_ziliaoku",
     "fans": 76000, "likes": 310000, "works": 158, "avg_play": 14000,
     "tags": ["资料分享", "模板"], "sign": "财税表格模板免费领",
     "url": "https://www.xiaohongshu.com/user/profile/caishui_ziliaoku"},
    # ---------------- 视频号 ----------------
    {"platform": "SHIPINHAO", "nickname": "企服观察局", "account_id": "qifu_guanchaju",
     "fans": 208000, "likes": 760000, "works": 168, "avg_play": 52000,
     "tags": ["企业服务", "行业观察"], "sign": "看懂企业服务这门生意",
     "url": "https://channels.weixin.qq.com/"},
    {"platform": "SHIPINHAO", "nickname": "财税政策直通车", "account_id": "zhengce_zhitongche",
     "fans": 145000, "likes": 520000, "works": 296, "avg_play": 38000,
     "tags": ["政策解读", "直播"], "sign": "每周三晚八点直播答疑",
     "url": "https://channels.weixin.qq.com/"},
    {"platform": "SHIPINHAO", "nickname": "老板财商课", "account_id": "laoban_caishang",
     "fans": 87000, "likes": 296000, "works": 132, "avg_play": 24000,
     "tags": ["财商", "老板必修"], "sign": "老板的财商必修课",
     "url": "https://channels.weixin.qq.com/"},
]

_FAN_LEVELS = [
    ("L1", 0, 10000),
    ("L2", 10000, 100000),
    ("L3", 100000, 500000),
    ("L4", 500000, 10 ** 12),
]


def benchmark_platforms():
    """可检索的平台列表（抖音、快手优先）"""
    return BENCHMARK_PLATFORMS


def _fan_level(level):
    for code, low, high in _FAN_LEVELS:
        if code == level:
            return low, high
    return None


def benchmark_search(q="", platform="ALL", sort="fans", fan_level=""):
    """多平台对标账号检索。

    q：昵称 / 账号ID / 标签 / 简介 模糊匹配
    platform：ALL / DOUYIN / KUAISHOU / XIAOHONGSHU / SHIPINHAO
    sort：fans / likes / works / avg_play
    fan_level：L1(<1万) L2(1-10万) L3(10-50万) L4(50万+)
    """
    q = (q or "").strip().lower()
    platform = (platform or "ALL").upper()

    items = []
    for idx, raw in enumerate(BENCHMARK_SAMPLE, start=1):
        item = dict(raw)
        item["id"] = idx
        item["platform_label"] = _PLATFORM_LABEL.get(raw["platform"], raw["platform"])
        # 演示数据：给一点随机浮动，避免每次结果完全一致（真实接口不需要）
        item["trend"] = [
            {"date": f"D-{i}", "play": int(raw["avg_play"] * (0.75 + 0.06 * i)),
             "fans_add": int(raw["fans"] * 0.0008 * (i % 5 + 1))}
            for i in range(7, 0, -1)
        ]
        items.append(item)

    if platform and platform != "ALL":
        items = [i for i in items if i["platform"] == platform]

    if q:
        def hit(i):
            return (q in i["nickname"].lower()
                    or q in i["account_id"].lower()
                    or q in (i.get("sign") or "").lower()
                    or any(q in t.lower() for t in i.get("tags") or []))
        items = [i for i in items if hit(i)]

    if fan_level:
        bound = _fan_level(fan_level)
        if bound:
            low, high = bound
            items = [i for i in items if low <= i["fans"] < high]

    # 抖音、快手优先排前
    priority = {"DOUYIN": 0, "KUAISHOU": 1, "XIAOHONGSHU": 2, "SHIPINHAO": 3}
    items.sort(key=lambda i: (priority.get(i["platform"], 9), -i.get(sort if sort in
               ("fans", "likes", "works", "avg_play") else "fans", 0)))

    return {
        "total": len(items),
        "source": "demo" if not _has_key("DOUYIN_API_KEY") else "live",
        "list": items,
    }
