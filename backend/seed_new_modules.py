"""种子数据：会员套餐 / 招商政策资料 / 专业基础知识子级文章（税务、发票、代理记账）
幂等：按 code/title 查重，已存在则跳过。
用法：cd backend && python seed_new_modules.py
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.membership.models import MembershipPlan, Subscription
from apps.investment.models import InvestPolicy, InvestMaterial, InvestInquiry
from apps.onboarding.models import KnowledgeArticle


def upsert_plan():
    plans = [
        {
            "code": "FREE", "name": "免费版", "price_monthly": 0, "price_yearly": 0,
            "level": 0, "sort_order": 0, "is_active": True,
            "features": ["基础经营总览", "公开课程试看", "企业查询演示"],
            "permissions": ["dashboard", "onboarding"],
        },
        {
            "code": "BASIC", "name": "基础版", "price_monthly": 199, "price_yearly": 1999,
            "level": 1, "sort_order": 1, "is_active": True,
            "features": ["全模块基础功能", "客户/合同管理", "在线考试与入职培训", "业绩中心查看"],
            "permissions": ["dashboard", "sales", "accounting", "hr", "ops",
                            "onboarding", "performance", "reports"],
        },
        {
            "code": "PRO", "name": "专业版", "price_monthly": 599, "price_yearly": 5999,
            "level": 2, "sort_order": 2, "is_active": True,
            "features": ["PRO 全部功能", "AI 经营助手", "招商板块", "数据权限墙", "对标账号搜索"],
            "permissions": ["dashboard", "sales", "accounting", "hr", "ops",
                            "onboarding", "performance", "reports", "ai", "investment"],
        },
        {
            "code": "FLAGSHIP", "name": "旗舰版", "price_monthly": 1999, "price_yearly": 19999,
            "level": 3, "sort_order": 3, "is_active": True,
            "features": ["全部功能无限开通", "会员管理后台", "优先技术支持", "专属客户成功经理"],
            "permissions": ["dashboard", "sales", "accounting", "hr", "ops",
                            "onboarding", "performance", "reports", "ai",
                            "investment", "membership"],
        },
    ]
    for p in plans:
        obj, created = MembershipPlan.objects.get_or_create(
            code=p["code"], defaults=p)
        if not created:
            for k, v in p.items():
                if k != "code":
                    setattr(obj, k, v)
            obj.save()
    print("会员套餐:", MembershipPlan.objects.count())


def upsert_invest():
    policies = [
        {
            "title": "城市合伙人政策", "sort_order": 0,
            "content": "面向有财税行业资源与本地服务能力的个人/机构开放城市合伙人。合伙人享受所辖城市新增客户分润（最高 30%）、总部品牌与系统赋能、线索定向派发。\n\n合作条件：具备本地工商/财税服务团队或稳定客户来源；认同平台交付标准；缴纳履约保证金（可退）。\n\n分润机制：按净增流水月度结算，阶梯上浮；连续 3 个月达标升级为独家合伙人。",
        },
        {
            "title": "渠道分润政策", "sort_order": 1,
            "content": "面向代账公司、财税服务商、园区招商团队开放渠道合作。渠道方通过专属邀请码发展客户，享受长期续费分润（15%~25%）与系统功能折扣。\n\n支持：统一后台查看名下客户与服务进度；总部承担交付与合规；渠道方专注获客。\n\n结算：T+1 可视，月度自动出账。",
        },
        {
            "title": "联营合作政策", "sort_order": 2,
            "content": "面向希望轻资产扩张的财税机构开放联营。双方按比例共担共盈，总部输出 SaaS 系统、培训认证、品牌与客诉中台，联营方输出本地团队与场地。\n\n适用：异地开分支、校园/产业园共建财税服务站。\n\n权责：标准化 SOP 交付，数据归属双方共有，退出机制写入合同。",
        },
    ]
    for p in policies:
        InvestPolicy.objects.get_or_create(title=p["title"], defaults=p)

    materials = [
        {"title": "财税企管云合作手册", "category": "MANUAL", "summary": "平台能力、合作模式、分润规则一页速览。", "file_url": "#", "sort_order": 0},
        {"title": "城市合伙人收益模型", "category": "MODEL", "summary": "以 100 家代账客户为例的回本与分润测算。", "file_url": "#", "sort_order": 1},
        {"title": "标杆合伙人案例", "category": "CASE", "summary": "西南某三线城市的 6 个月从 0 到 300 客案例拆解。", "file_url": "#", "sort_order": 2},
        {"title": "品牌与物料素材包", "category": "BRAND", "summary": "logo、海报、宣讲 PPT、短视频脚本合集。", "file_url": "#", "sort_order": 3},
    ]
    for m in materials:
        InvestMaterial.objects.get_or_create(title=m["title"], defaults=m)
    print("招商政策:", InvestPolicy.objects.count(), "招商资料:", InvestMaterial.objects.count())


def upsert_articles():
    def add(category, title, content, summary="", level="BASIC", sort=0):
        obj, created = KnowledgeArticle.objects.get_or_create(
            category=category, title=title,
            defaults={"content": content, "summary": summary, "level": level,
                      "is_published": True, "is_required": True, "sort": sort})
        return created

    # 代理记账（补全 Boss 点名的二级子项）
    add("AGENCY", "什么是代理记账",
        "代理记账是指企业将会计核算、记账、报税等财税工作委托给有资质的中介机构（代理记账公司）完成，企业只设出纳、保留原始凭证。\n\n政策依据：《会计法》第三十六条明确，不具备设置会计机构条件的单位应委托经批准设立的中介代理记账。代理记账机构须有 3 名以上专职从业人员并持有代理记账许可证书。\n\n适用对象：小微企业、初创公司、个体工商户——用人成本低、专业度高、合规风险可控。",
        "一句话讲清代理记账的定义、政策依据与适用对象", sort=0)
    add("AGENCY", "代理记账公司标准服务流程",
        "标准服务流程分六步：①签订协议明确服务范围与责任；②交接资料（银行流水、发票、合同等）建立客户档案；③建账与初始化（科目设置、期初余额）；④日常记账与凭证编制；⑤按期纳税申报（增值税、企业所得税、个税等）；⑥月度/季度出具财务报表并归档。\n\n交付物：记账凭证、明细账、总账、资产负债表、利润表、纳税回执。全流程留痕可追溯。",
        "代理记账从签约到申报的标准六步", sort=1)

    # 税务知识（子级：流程 / 等级 / 合规）
    add("TAX", "税务申报办理流程",
        "企业纳税申报标准流程：①按期汇总收入、成本、进项税额等数据；②登录电子税务局或用开票/申报软件录入；③系统校验比对（票表比对、勾稽关系）；④确认申报并扣缴税款；⑤留存申报表与完税凭证。\n\n期限：增值税及附加一般按月（小规模按季）；企业所得税按季预缴、年终汇算清缴；个税代扣代缴按月。逾期将产生滞纳金与信用影响。",
        "从数据汇总到缴税的申报全流程", sort=0)
    add("TAX", "纳税人信用等级与分类",
        "税务机关对纳税人按信用分级：A 级（年度评价指标≥90 分，激励：按需领票、少检查）、B 级（70~90，正常）、M 级（新办企业，无生产经营收入）、C 级（40~70，从严管理）、D 级（<40 或重大违法，惩戒：限量供票、高频检查）。\n\n信用等级直接影响发票额度、检查频率与融资授信，企业应重视合规记分（如按时申报、如实填开）。",
        "A/B/M/C/D 五级信用含义与影响", sort=1)
    add("TAX", "常见税种计算逻辑",
        "增值税=销项税额−进项税额（一般计税）；企业所得税=应纳税所得额×税率（小型微利企业有优惠）；附加税（城建/教育费附加）以增值税为基数；印花税按合同金额比例。\n\n小微优惠：符合条件的小型微利企业年应纳税所得额≤300 万部分实际税负显著降低；小规模纳税人月销售额未达起征点免征增值税。",
        "增值税/所得税/附加税核心算法", sort=2)
    add("TAX", "税务合规风险提示",
        "高频风险：长期零申报、进销项严重不匹配、公转私无依据、虚开发票、逾期申报。\n\n建议：业务真实、票流货流资金流一致；取得合规进项票；按时申报即便无收入也做零申报；重大交易前置咨询。违规轻则补税滞纳金，重则列入 D 级并移送稽查。",
        "企业最常见税务违规与规避建议", sort=3)

    # 发票管理（子级：流程 / 等级 / 查验）
    add("INVOICE", "发票开具标准流程",
        "开票流程：①确认购方名称、税号、地址电话、开户行账号；②选择正确商品税收分类编码与税率；③系统开具并打印/推送电子发票；④交付购方并留存底账。\n\n要点：内容真实、品名具体、金额与实际一致；专票需购方完整信息；错开需及时红冲重开。",
        "从填开到交付的标准开票流程", sort=0)
    add("INVOICE", "发票种类与等级划分",
        "按用途分：增值税专用发票（可抵扣进项，需一般纳税人）与增值税普通发票（不可抵扣）；电子发票与纸质发票具同等效力。\n\n按额度/授信：新办企业初始为普通发票、限额较低；随经营与信用提升可申请增版增量（如万元版→十万元版）。发票等级本质由税务机关按信用与经营核定授信额度。",
        "专票/普票/电子票与授信等级", sort=1)
    add("INVOICE", "发票查验与认证",
        "查验：通过全国增值税发票查验平台或省电子税务局输入发票代码、号码、金额、日期核验真伪。\n\n认证抵扣：一般纳税人取得专票后，在勾选确认平台勾选、申报期抵扣；逾期未勾选或异常发票不得抵扣。建议收票即验真、按月勾选，避免超期。",
        "发票真伪查验与专票勾选认证", sort=2)
    add("INVOICE", "虚开发票风险警示",
        "虚开指无真实交易开票、为他人/让他人为自己虚开、介绍虚开。属严重违法，触犯刑法（虚开增值税专用发票罪），可追刑责并列入税收违法黑名单。\n\n红线：票流、资金流、货物流（或服务流）必须一致；不以税点为利；不买卖发票。企业遇「富余票」兜售一律拒绝并举报。",
        "虚开界定与刑事红线警示", sort=3)

    print("知识文章(代理/税务/发票)条数:",
          KnowledgeArticle.objects.filter(category__in=["AGENCY", "TAX", "INVOICE"]).count())


if __name__ == "__main__":
    upsert_plan()
    upsert_invest()
    upsert_articles()
    print("种子完成。")
