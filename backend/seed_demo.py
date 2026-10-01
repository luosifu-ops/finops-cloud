# -*- coding: utf-8 -*-
"""演示数据初始化脚本
用法：python seed_demo.py         (写入演示数据)
      python seed_demo.py reset  (清空业务数据后重建)
"""
import os
import sys
import random
from datetime import date, timedelta, time as dtime, datetime

import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.utils import timezone
from apps.accounts.models import User, Department, Team, Position
from apps.hr.models import AttendanceRule, Attendance, LeaveApplication
from apps.onboarding.models import (CultureArticle, Regulation, KnowledgeArticle,
                                    QuestionBank, Question, Exam, OnboardingTask)
from apps.sales.models import Lead, Customer, Contract, CallRecord, SalesTarget, CommissionRule
from apps.accounting.models import (AccountingClient, MonthlyTask, TaxType, TaxDeclaration,
                                    BusinessItem, AnnualReport)
from apps.ops.models import AdPlatform, AdAccount, AdCampaign, AdDailyStat, ChannelBudget, ContentPost
from apps.reports.models import DailyReport, MonthlyReport

random.seed(20260901)
TODAY = date(2026, 9, 1)
MONTH = "2026-09"
LAST_MONTH = "2026-08"

NAMES = ["张伟", "李娜", "王强", "刘洋", "陈静", "杨磊", "赵敏", "黄超", "周婷", "吴昊",
         "徐倩", "孙鹏", "马丽", "朱峰", "胡蓉", "郭浩", "林芳", "何军", "高敏", "罗成"]
SURNAMES = NAMES


def month_range(month):
    y, m = int(month[:4]), int(month[5:7])
    start = date(y, m, 1)
    end = date(y + 1, 1, 1) - timedelta(days=1) if m == 12 else date(y, m + 1, 1) - timedelta(days=1)
    return start, end


def daterange(start, end):
    for i in range((end - start).days + 1):
        yield start + timedelta(days=i)


def log(msg):
    print(f"  ✓ {msg}")


def reset_data():
    print("清空旧业务数据...")
    for m in [Contract, Customer, Lead, CallRecord, AdDailyStat, ContentPost, AccountingClient,
              MonthlyTask, Attendance, LeaveApplication, DailyReport, MonthlyReport,
              Exam, Question, QuestionBank, KnowledgeArticle, Regulation, CultureArticle,
              OnboardingTask, SalesTarget, CommissionRule, ChannelBudget]:
        m.objects.all().delete()
    User.objects.exclude(username="admin").delete()
    Department.objects.all().delete()
    AdPlatform.objects.all().delete()
    TaxType.objects.all().delete()
    log("已清空（保留超级管理员）")


def create_org():
    print("\n[1/8] 组织架构与员工")
    depts = {}
    for code, name, desc in [
        ("SALES", "电销部", "负责线索转化、客户签约、回款跟进"),
        ("ACCOUNT", "会计部", "负责代理记账、纳税申报、工商事项办理"),
        ("OPS", "运营部", "负责各平台投放获客、内容运营、引流转化"),
        ("MGMT", "管理层", "公司整体经营与决策"),
    ]:
        depts[code] = Department.objects.create(name=name, code=code, description=desc)
    log(f"创建 {len(depts)} 个部门")

    # 老板
    boss = User.objects.create_superuser("boss", "boss@company.com", "admin123")
    boss.first_name = "罗"
    boss.last_name = "总"
    boss.role = "BOSS"
    boss.status = "REGULAR"
    boss.department = depts["MGMT"]
    boss.employee_no = "M001"
    boss.phone = "13800000001"
    boss.entry_date = date(2018, 3, 1)
    boss.save()
    log("老板账号：boss / admin123")

    teams = {}
    teams["SALES1"] = Team.objects.create(name="电销一组", department=depts["SALES"], month_target=150000)
    teams["SALES2"] = Team.objects.create(name="电销二组", department=depts["SALES"], month_target=150000)

    users = {"boss": boss}
    # 部门经理
    managers = [
        ("sales_mgr", "李", "娜", "SALES", "MANAGER", "S001", 160000),
        ("acc_mgr", "陈", "静", "ACCOUNT", "MANAGER", "A001", 0),
        ("ops_mgr", "杨", "磊", "OPS", "MANAGER", "O001", 0),
    ]
    for uname, fn, ln, dcode, role, no, target in managers:
        u = User.objects.create_user(uname, f"{uname}@company.com", "123456")
        u.first_name, u.last_name = fn, ln
        u.role, u.status = role, "REGULAR"
        u.department = depts[dcode]
        u.employee_no = no
        u.phone = "138" + str(random.randint(10000000, 99999999))
        u.entry_date = date(2020, random.randint(1, 12), random.randint(1, 28))
        u.month_target = target
        u.save()
        users[uname] = u
        depts[dcode].leader = u
        depts[dcode].save()
    log("3 名部门经理（销售/会计/运营）")

    # 销售员工 8 人
    idx = 0
    for i in range(8):
        idx += 1
        uname = f"sales{idx}"
        u = User.objects.create_user(uname, f"{uname}@company.com", "123456")
        u.first_name = NAMES[idx % len(NAMES)][0]
        u.last_name = NAMES[idx % len(NAMES)][1:]
        u.role = "LEADER" if idx == 1 else "EMPLOYEE"
        u.status = "REGULAR" if idx % 3 else "PROBATION"
        u.department = depts["SALES"]
        u.team = teams["SALES1"] if idx <= 4 else teams["SALES2"]
        u.employee_no = f"S{100 + idx}"
        u.phone = "139" + str(random.randint(10000000, 99999999))
        u.entry_date = date(2024, random.randint(1, 12), random.randint(1, 28))
        u.month_target = random.choice([30000, 40000, 50000, 60000])
        u.save()
        users[uname] = u
    teams["SALES1"].leader = users["sales1"]
    teams["SALES1"].save()
    teams["SALES2"].leader = users["sales5"]
    teams["SALES2"].save()

    # 会计 5 人
    for i in range(5):
        uname = f"acc{i+1}"
        u = User.objects.create_user(uname, f"{uname}@company.com", "123456")
        u.first_name = NAMES[(i + 5) % len(NAMES)][0]
        u.last_name = NAMES[(i + 5) % len(NAMES)][1:]
        u.role = "EMPLOYEE"
        u.status = "REGULAR"
        u.department = depts["ACCOUNT"]
        u.employee_no = f"A{100 + i}"
        u.phone = "137" + str(random.randint(10000000, 99999999))
        u.entry_date = date(2023, random.randint(1, 12), random.randint(1, 28))
        u.save()
        users[uname] = u

    # 运营 3 人
    for i in range(3):
        uname = f"ops{i+1}"
        u = User.objects.create_user(uname, f"{uname}@company.com", "123456")
        u.first_name = NAMES[(i + 10) % len(NAMES)][0]
        u.last_name = NAMES[(i + 10) % len(NAMES)][1:]
        u.role = "EMPLOYEE"
        u.status = "REGULAR"
        u.department = depts["OPS"]
        u.employee_no = f"O{100 + i}"
        u.phone = "136" + str(random.randint(10000000, 99999999))
        u.entry_date = date(2024, random.randint(1, 12), random.randint(1, 28))
        u.save()
        users[uname] = u

    # 人事
    hr = User.objects.create_user("hr", "hr@company.com", "123456")
    hr.first_name, hr.last_name = "周", "婷"
    hr.role, hr.status = "HR", "REGULAR"
    hr.department = depts["MGMT"]
    hr.employee_no = "H001"
    hr.save()
    users["hr"] = hr

    log(f"共创建 {User.objects.count()} 名员工")
    return depts, teams, users


def create_onboarding():
    print("\n[2/8] 入职培训体系")
    cultures = [
        ("公司简介", "INTRO", "昆明XX财税服务有限公司成立于 2018 年，专注为中小微企业提供"
                              "公司注册、代理记账、税务筹划、工商变更注销等一站式财税服务。"
                              "目前服务在册客户 800+ 家，覆盖昆明及周边地州。"),
        ("我们的使命", "VISION", "让每一家小微企业都用得起、用得放心的专业财税服务。"
                                "三年内成为云南本地客户口碑第一的财税服务商。"),
        ("价值观", "VALUE", "客户第一：客户的合规与安全永远排在业绩前面。\n"
                          "专业立身：不懂就问，不装懂，不做没把握的承诺。\n"
                          "结果说话：用数据和交付结果证明价值。\n"
                          "长期主义：不赚快钱，只做能积累的事。"),
    ]
    for i, (title, cat, content) in enumerate(cultures):
        CultureArticle.objects.create(title=title, category=cat, content=content, sort=i)
    log(f"企业文化 {len(cultures)} 篇")

    regs = [
        ("考勤管理制度", "ATTENDANCE", "V1.2",
         "一、工作时间：周一至周六 9:00-18:00，午休 12:00-13:30。\n"
         "二、打卡：每日上下班各打卡一次，忘记打卡需当日提交补卡申请。\n"
         "三、迟到：9:10 后到岗记为迟到，当月累计 3 次迟到扣 50 元。\n"
         "四、旷工：未请假且未到岗视为旷工，旷工一天扣 3 天工资。\n"
         "五、请假：需提前在系统提交，1 天内组长审批，2 天以上部门经理审批。"),
        ("薪酬绩效制度", "SALARY", "V1.1",
         "一、销售岗：底薪 + 提成，提成按回款金额阶梯计算。\n"
         "二、会计岗：底薪 + 户数补贴 + 质量奖金（无逾期无投诉）。\n"
         "三、运营岗：底薪 + 线索量奖金 + ROI 达成奖金。\n"
         "四、发薪日：每月 15 日发放上月工资。"),
        ("保密与合规制度", "SECRET", "V1.0",
         "一、严禁泄露客户财务数据、身份信息、税务账号密码。\n"
         "二、严禁私自以公司名义对外承诺、收款。\n"
         "三、严禁向客户推介任何理财、股票、虚拟币产品。\n"
         "四、违反者立即解除劳动合同并追究法律责任。"),
        ("费用报销制度", "EXPENSE", "V1.0",
         "一、单笔 500 元以下由部门经理审批，500 元以上需总经理审批。\n"
         "二、报销需附发票或收据，当月费用当月报销。\n"
         "三、客户招待费需注明客户名称与事由。"),
        ("日常行为规范", "BEHAVIOR", "V1.0",
         "一、工作时间内禁止做与工作无关的事。\n"
         "二、客户沟通须使用公司统一话术，严禁虚假承诺。\n"
         "三、每日 18:30 前提交日报，未提交按制度扣款。"),
    ]
    for title, cat, ver, content in regs:
        Regulation.objects.create(title=title, category=cat, version=ver, content=content,
                                  effective_date=date(2026, 1, 1))
    log(f"公司制度 {len(regs)} 项")

    articles = [
        ("什么是代理记账？", "AGENCY", "BASIC",
         "代理记账是指企业将会计核算、记账、报税等工作委托给专业记账公司完成，"
         "企业只设立出纳人员负责日常货币收支和财产保管。适合不具备独立设置会计机构条件的中小微企业。"),
        ("小规模纳税人与一般纳税人的区别", "TAX", "BASIC",
         "小规模纳税人：年应税销售额 ≤500 万元，增值税按征收率 3%（现优惠 1%）简易计税，"
         "不能抵扣进项。\n一般纳税人：可开具专票、可抵扣进项，税率 6%/9%/13%，账务要求更高。"
         "选择哪种要看客户规模、客户对象是否需要专票、进项票是否充足。"),
        ("增值税申报要点", "TAX", "MIDDLE",
         "小规模纳税人按季申报（1/4/7/10 月 15 日前），一般纳税人按月申报（次月 15 日前）。\n"
         "常见风险：开票金额与申报收入不一致、漏报未开票收入、进项认证逾期。"),
        ("企业所得税怎么算", "TAX", "MIDDLE",
         "应纳税额 = 应纳税所得额 × 税率 - 减免税额 - 抵免税额。\n"
         "小微企业所得税优惠：年应纳税所得额 ≤300 万部分，实际税负 5%。\n"
         "按季预缴，次年 5 月 31 日前汇算清缴。"),
        ("发票管理六不准", "INVOICE", "BASIC",
         "不准虚开、不准代开、不准拆本使用、不准转借转让、不准擅自损毁、不准跨区携带空白发票。\n"
         "收到进项票先看四流一致：合同流、发票流、资金流、货物流。"),
        ("工商注册全流程", "BUSINESS", "BASIC",
         "核名 → 提交材料 → 领取执照 → 刻章 → 银行开户 → 税务报到 → 票种核定。\n"
         "昆明目前全流程电子化，正常 3-5 个工作日可下照。"),
        ("公司注销为什么难", "BUSINESS", "ADVANCED",
         "注销难在税务清税：需结清所有税款、缴销发票、解除非正常户。\n"
         "常见卡点：长期零申报被列入风险纳税人、地址异常、股东失联、账目混乱。\n"
         "简易注销适用于未开业、无债权债务的企业，公示 20 天。"),
        ("社保公积金开户与申报", "SOCIAL", "BASIC",
         "新开户需营业执照、法人身份证、银行开户许可、公章。\n"
         "每月申报期为 1-25 日，申报后需按时足额缴纳，逾期产生滞纳金。"),
        ("做账软件常用操作", "SOFTWARE", "BASIC",
         "凭证录入 → 审核 → 记账 → 结转损益 → 生成报表 → 报税。\n"
         "注意：凭证录入后必须审核，未审核凭证不进入账簿。"),
        ("电销开场白话术", "SALE", "BASIC",
         "黄金 15 秒：自报家门 + 说明来意 + 抛出利益点。\n"
         "示例：'您好，我是昆明XX财税的小李，看到您在XX平台咨询过注册公司，"
         "我们昆明本地 3 天下照、送一年代账，方便加个微信发份报价给您吗？'"),
    ]
    for i, (title, cat, level, content) in enumerate(articles):
        KnowledgeArticle.objects.create(title=title, category=cat, level=level,
                                        content=content, summary=content[:60], sort=i)
    log(f"财税知识文章 {len(articles)} 篇")

    bank = QuestionBank.objects.create(name="新人财税基础考试", description="入职第一周必考")
    qs = [
        ("SINGLE", "小规模纳税人的增值税征收率通常为？",
         [{"key": "A", "text": "3%"}, {"key": "B", "text": "6%"},
          {"key": "C", "text": "9%"}, {"key": "D", "text": "13%"}],
         "A", "小规模纳税人适用 3% 征收率，现行优惠为减按 1%。"),
        ("SINGLE", "企业所得税汇算清缴的截止日期是？",
         [{"key": "A", "text": "3月31日"}, {"key": "B", "text": "5月31日"},
          {"key": "C", "text": "6月30日"}, {"key": "D", "text": "12月31日"}],
         "B", "次年 5 月 31 日前完成汇算清缴。"),
        ("JUDGE", "代理记账公司可以代客户保管税控盘和 UK。",
         [], "对", "实务中由代账公司保管税控设备需在服务协议中明确约定。"),
        ("JUDGE", "一般纳税人可以抵扣进项税额。", [], "对",
         "一般纳税人取得合规增值税专用发票可认证抵扣。"),
        ("SINGLE", "公司注销流程中，最关键的环节是？",
         [{"key": "A", "text": "工商注销"}, {"key": "B", "text": "税务清税"},
          {"key": "C", "text": "银行销户"}, {"key": "D", "text": "登报公告"}],
         "B", "税务清税是难点，需结清税款、缴销发票、解除非正常。"),
        ("MULTI", "以下哪些属于增值税纳税申报的必备资料？",
         [{"key": "A", "text": "资产负债表"}, {"key": "B", "text": "利润表"},
          {"key": "C", "text": "增值税申报表"}, {"key": "D", "text": "员工花名册"}],
         "ABC", "增值税申报需附财务报表，员工花名册不是必备。"),
        ("SINGLE", "发票的“四流一致”不包括？",
         [{"key": "A", "text": "合同流"}, {"key": "B", "text": "发票流"},
          {"key": "C", "text": "资金流"}, {"key": "D", "text": "人员流"}],
         "D", "四流指合同流、发票流、资金流、货物流（或服务流）。"),
        ("SINGLE", "小微企业所得税优惠的实际税负是？",
         [{"key": "A", "text": "2.5%"}, {"key": "B", "text": "5%"},
          {"key": "C", "text": "15%"}, {"key": "D", "text": "25%"}],
         "B", "年应纳税所得额不超过 300 万部分，实际税负 5%。"),
        ("JUDGE", "发现客户要求虚开发票时，应当拒绝并上报主管。", [], "对",
         "虚开发票属违法行为，必须拒绝，必要时终止服务。"),
        ("MULTI", "新公司注册后必须办理的事项包括？",
         [{"key": "A", "text": "刻章"}, {"key": "B", "text": "银行开户"},
          {"key": "C", "text": "税务报到"}, {"key": "D", "text": "申请高新企业"}],
         "ABC", "刻章、开户、税务报到是必经流程，高新企业为可选项。"),
        ("SINGLE", "客户长期零申报可能导致？",
         [{"key": "A", "text": "被列为风险纳税人"}, {"key": "B", "text": "自动注销"},
          {"key": "C", "text": "降低税率"}, {"key": "D", "text": "无需报税"}],
         "A", "长期零申报会被税局标记为风险纳税人，影响注销与发票领用。"),
        ("SINGLE", "代理记账的服务核心交付物是？",
         [{"key": "A", "text": "营业执照"}, {"key": "B", "text": "记账凭证与纳税申报"},
          {"key": "C", "text": "公司公章"}, {"key": "D", "text": "银行流水"}],
         "B", "代账核心是做账凭证 + 财务报表 + 按时申报。"),
    ]
    for qtype, stem, opts, ans, ana in qs:
        Question.objects.create(bank=bank, qtype=qtype, stem=stem, options=opts,
                                answer=ans, analysis=ana, score=10 if qtype != "MULTI" else 15)
    log(f"题库 {Question.objects.count()} 道题")

    Exam.objects.create(title="新人入职财税基础考试", bank=bank, question_count=10,
                        total_score=100, pass_score=60, duration=45,
                        status="PUBLISHED", description="覆盖代账基础、税务常识、发票管理、工商流程")

    tasks = [
        ("阅读《公司简介》与《我们的使命》", "COURSE"),
        ("阅读并确认全部公司制度", "REGULATION"),
        ("学习《什么是代理记账？》", "COURSE"),
        ("学习《小规模纳税人与一般纳税人的区别》", "COURSE"),
        ("学习《发票管理六不准》", "COURSE"),
        ("通过《新人入职财税基础考试》", "EXAM"),
        ("提交入职资料（身份证、学历证、银行卡）", "MATERIAL"),
    ]
    for i, (title, ttype) in enumerate(tasks):
        OnboardingTask.objects.create(title=title, task_type=ttype, sort=i, due_days=7)
    log(f"入职任务清单 {len(tasks)} 项")


def create_ops(users):
    print("\n[3/8] 运营部投放数据")
    platforms = {}
    for code, name in [("AMAP", "高德地图"), ("BAIDU", "百度推广"),
                       ("XIAOHONGSHU", "小红书"), ("DOUYIN", "抖音")]:
        platforms[code] = AdPlatform.objects.create(
            name=name, code=code, contact=["王经理", "李经理", "张经理", "赵经理"][len(platforms) % 4],
            has_api=False)
    log(f"投放平台 {len(platforms)} 个：高德 / 百度 / 小红书 / 抖音")

    ops_users = [users.get("ops1"), users.get("ops2"), users.get("ops3")]
    accounts = {}
    for code, p in platforms.items():
        accounts[code] = AdAccount.objects.create(
            platform=p, name=f"{p.name}主账户", account_id=f"{code}2026",
            owner=random.choice(ops_users), daily_budget=random.choice([800, 1200, 1500, 2000]),
            month_budget=random.choice([24000, 36000, 45000, 60000]),
            balance=random.randint(5000, 30000))

    campaigns = {}
    for code, acc in accounts.items():
        for i, biz in enumerate(["公司注册", "代理记账"]):
            campaigns[f"{code}_{i}"] = AdCampaign.objects.create(
                account=acc, name=f"{acc.platform.name}-{biz}",
                biz_line=biz, city="昆明", goal="线索",
                start_date=TODAY - timedelta(days=90))

    # 近 60 天投放数据
    start = TODAY - timedelta(days=59)
    base = {"AMAP": (680, 26, 9), "BAIDU": (820, 30, 11),
            "XIAOHONGSHU": (420, 22, 7), "DOUYIN": (900, 38, 12)}
    for d in daterange(start, TODAY):
        for code, acc in accounts.items():
            cost_avg, lead_avg, deal_week = base[code]
            factor = 0.75 + random.random() * 0.5
            cost = round(cost_avg * factor, 2)
            leads = max(0, int(lead_avg * factor + random.randint(-4, 4)))
            valid = int(leads * random.uniform(0.55, 0.8))
            wechat = int(valid * random.uniform(0.5, 0.85))
            visit = int(wechat * random.uniform(0.2, 0.45))
            deal = int(wechat * random.uniform(0.08, 0.2))
            amount = deal * random.choice([1800, 2400, 3000, 3600, 4800])
            for ckey in [f"{code}_0", f"{code}_1"]:
                share = 0.6 if ckey.endswith("0") else 0.4
                AdDailyStat.objects.update_or_create(
                    platform=platforms[code], account=acc, campaign=campaigns[ckey], date=d,
                    defaults=dict(
                        cost=round(cost * share, 2),
                        impression=int(leads * random.randint(120, 260) * share),
                        click=int(leads * random.randint(6, 15) * share),
                        lead_count=int(leads * share),
                        valid_lead=int(valid * share),
                        wechat_added=int(wechat * share),
                        visit_count=int(visit * share),
                        deal_count=int(deal * share),
                        deal_amount=round(amount * share, 2),
                        operator=random.choice(ops_users),
                    ))
    log(f"投放日报 {AdDailyStat.objects.count()} 条（近 60 天 × 4 平台 × 2 计划）")

    for code, p in platforms.items():
        ChannelBudget.objects.create(month=MONTH, platform=p,
                                     budget=base[code][0] * 30,
                                     lead_target=base[code][1] * 30,
                                     deal_target=int(base[code][1] * 30 * 0.12))
    log("本月渠道预算已设置")

    for i, (title, plat, kind) in enumerate([
        ("昆明注册公司需要多久？全流程拆解", "XIAOHONGSHU", "NOTE"),
        ("代记账 vs 请会计，一年差多少钱", "DOUYIN", "VIDEO"),
        ("小规模纳税人开票超 500 万怎么办", "XIAOHONGSHU", "NOTE"),
        ("公司不做账不报税的 5 个后果", "DOUYIN", "VIDEO"),
        ("昆明创业补贴怎么领", "XIAOHONGSHU", "NOTE"),
    ]):
        ContentPost.objects.create(
            title=title, platform=plat, kind=kind,
            author=random.choice(ops_users),
            publish_at=timezone.make_aware(datetime.combine(
                TODAY - timedelta(days=random.randint(1, 30)), dtime(10, 0))),
            status="PUBLISHED",
            script=f"【{title}】开头 3 秒抛出痛点，中段给方法，结尾引导私信咨询。")
    log(f"内容作品 {ContentPost.objects.count()} 条")


def create_sales(depts, teams, users):
    print("\n[4/8] 电销部业务数据")
    sales_users = list(User.objects.filter(department__code="SALES", role="EMPLOYEE")) + \
                  list(User.objects.filter(department__code="SALES", role="LEADER"))
    if not sales_users:
        sales_users = [users["sales1"]]
    mgr = users["sales_mgr"]
    sales_users.insert(0, mgr)

    sources = ["AMAP", "BAIDU", "XIAOHONGSHU", "DOUYIN", "REFERRAL", "OFFLINE"]
    biz = ["公司注册", "代理记账", "公司注销", "工商变更", "地址挂靠"]
    levels = ["A", "B", "C", "C", "D"]

    leads = []
    for i in range(120):
        d = TODAY - timedelta(days=random.randint(0, 59))
        status = random.choices(["NEW", "ASSIGNED", "FOLLOWING", "INTENTION", "DEAL", "LOST", "INVALID"],
                                weights=[5, 15, 30, 15, 18, 12, 5])[0]
        lead = Lead.objects.create(
            name=f"{random.choice(['王','李','张','刘','陈','杨','赵','黄','周','吴'])}"
                 f"{random.choice(['总','经理','女士','先生','哥','姐'])}",
            phone="1" + str(random.randint(30, 99)) + str(random.randint(10000000, 99999999)),
            company=f"昆明{random.choice(['云','滇','鑫','博','汇','达','诚','安'])}"
                    f"{random.choice(['商贸','科技','装饰','餐饮','物流','咨询'])}有限公司",
            source=random.choice(sources),
            intention=random.choice(biz),
            level=random.choice(levels),
            status=status,
            owner=random.choice(sales_users) if status != "NEW" else None,
            assigned_at=timezone.make_aware(datetime.combine(d, dtime(9, 0))) if status != "NEW" else None,
            dealt_at=timezone.make_aware(datetime.combine(d, dtime(15, 0))) if status == "DEAL" else None,
            lost_reason=random.choice(["价格贵", "已找同行", "暂时不需要", "联系不上"]) if status == "LOST" else "",
            created_at=timezone.make_aware(datetime.combine(d, dtime(random.randint(9, 18), 0))),
        )
        leads.append(lead)
    log(f"销售线索 {len(leads)} 条")

    # 客户 + 合同
    customers = []
    for i in range(45):
        c = Customer.objects.create(
            name=f"昆明{random.choice(['云','滇','鑫','博','汇','达','诚','安','泰','恒'])}"
                 f"{random.choice(['商贸','科技','装饰','餐饮','物流','咨询','建材'])}有限公司",
            customer_type=random.choice(["ENTERPRISE", "ENTERPRISE", "INDIVIDUAL"]),
            contact=f"{random.choice(['王','李','张','刘','陈'])}经理",
            phone="1" + str(random.randint(30, 99)) + str(random.randint(10000000, 99999999)),
            industry=random.choice(["批发零售", "建筑装修", "餐饮服务", "信息技术", "物流运输"]),
            region=random.choice(["五华区", "盘龙区", "官渡区", "西山区", "呈贡区"]),
            source=random.choice(sources),
            owner=random.choice(sales_users),
            level=random.choice(["A", "B", "C"]),
            signed_at=TODAY - timedelta(days=random.randint(10, 400)),
        )
        c.expire_at = (c.signed_at or TODAY) + timedelta(days=365)
        c.save()
        customers.append(c)
    log(f"客户档案 {len(customers)} 家")

    for m in [LAST_MONTH, MONTH]:
        s, e = month_range(m)
        for i in range(random.randint(28, 38)):
            c = random.choice(customers)
            sign = s + timedelta(days=random.randint(0, (min(e, TODAY) - s).days)) if s < TODAY else s
            if sign > TODAY:
                continue
            amount = random.choice([1800, 2400, 3000, 3600, 4800, 6000, 8800, 12000])
            received = amount if random.random() > 0.3 else round(amount * 0.5, 2)
            Contract.objects.create(
                contract_no=f"HT{m.replace('-', '')}{1000 + random.randint(0, 8999)}",
                customer=c,
                biz_type=random.choice(["AGENCY", "AGENCY", "REGISTER", "CHANGE", "CANCEL"]),
                title=f"{c.name} 财税服务合同",
                amount=amount, received=received,
                pay_type=random.choice(["FULL", "FULL", "DEPOSIT", "MONTHLY"]),
                sales=random.choice(sales_users),
                status="PAID" if received >= amount else "EXECUTING",
                signed_date=sign,
                start_date=sign,
                end_date=sign + timedelta(days=365),
            )
    log(f"合同订单 {Contract.objects.count()} 份（{LAST_MONTH} + {MONTH}）")

    # 通话记录
    for u in sales_users:
        for d in daterange(TODAY - timedelta(days=29), TODAY):
            for _ in range(random.randint(35, 90)):
                CallRecord.objects.create(
                    user=u, phone="1" + str(random.randint(30, 99)) + str(random.randint(10000000, 99999999)),
                    duration=random.randint(10, 300),
                    result=random.choices(["CONNECTED", "NO_ANSWER", "REJECTED", "SHUTDOWN"],
                                          weights=[45, 30, 15, 10])[0],
                    has_wechat=random.random() > 0.75,
                    created_at=timezone.make_aware(datetime.combine(d, dtime(random.randint(9, 18)))),
                )
    log(f"通话记录 {CallRecord.objects.count()} 条（近 30 天）")

    SalesTarget.objects.create(month=MONTH, scope="COMPANY", amount_target=400000)
    SalesTarget.objects.create(month=MONTH, scope="DEPARTMENT", department=depts["SALES"], amount_target=300000)
    for t in Team.objects.filter(department=depts["SALES"]):
        SalesTarget.objects.create(month=MONTH, scope="TEAM", team=t, amount_target=t.month_target)
    for u in sales_users:
        SalesTarget.objects.create(month=MONTH, scope="PERSON", user=u, amount_target=u.month_target)
    CommissionRule.objects.create(name="销售阶梯提成", rule_type="LADDER", department=depts["SALES"],
                                  ladder=[{"min": 0, "max": 30000, "rate": 5},
                                          {"min": 30000, "max": 60000, "rate": 8},
                                          {"min": 60000, "max": 1000000, "rate": 12}],
                                  effective_month=MONTH)
    log("业绩目标与提成规则已配置")


def create_accounting(depts, users):
    print("\n[5/8] 会计部做账数据")
    for name, cycle, rule in [
        ("增值税", "MONTH", "次月15日前"), ("企业所得税", "QUARTER", "季后15日内"),
        ("个人所得税", "MONTH", "次月15日前"), ("城市维护建设税", "MONTH", "次月15日前"),
        ("教育费附加", "MONTH", "次月15日前"), ("印花税", "QUARTER", "季后15日内"),
    ]:
        TaxType.objects.create(name=name, cycle=cycle, deadline_rule=rule)
    log(f"税种 {TaxType.objects.count()} 项")

    acc_users = list(User.objects.filter(department__code="ACCOUNT"))
    customers = list(Customer.objects.all()[:30])
    acc_clients = []
    for i, c in enumerate(customers):
        ac = AccountingClient.objects.create(
            customer=c,
            accountant=random.choice(acc_users),
            taxpayer_type=random.choices(["SMALL", "GENERAL", "INDIVIDUAL"], weights=[70, 20, 10])[0],
            tax_no=f"91530100MA6{random.randint(10000000, 99999999)}",
            tax_bureau=random.choice(["五华区税务局", "盘龙区税务局", "官渡区税务局"]),
            status=random.choices(["ACTIVE", "ACTIVE", "ACTIVE", "PAUSED"], weights=[80, 10, 5, 5])[0],
            service_start=c.signed_at or TODAY,
            service_end=(c.signed_at or TODAY) + timedelta(days=365),
            monthly_fee=random.choice([200, 300, 300, 400, 500, 600]),
            zero_declare=random.random() > 0.7,
        )
        acc_clients.append(ac)
    log(f"代账客户 {len(acc_clients)} 家")

    # 上月的做账任务（大部分已完成）
    for ac in acc_clients:
        deadline_last = date(2026, 9, 15)
        done = random.random() > 0.12
        t = MonthlyTask.objects.create(
            client=ac, period=LAST_MONTH, accountant=ac.accountant,
            status="DONE" if done else random.choice(["DOING", "WAIT_DOC"]),
            doc_received_at=date(2026, 9, random.randint(1, 8)),
            voucher_done_at=date(2026, 9, random.randint(8, 13)) if done else None,
            declared_at=date(2026, 9, random.randint(10, 15)) if done else None,
            deadline=deadline_last,
            income=random.randint(0, 300000),
            cost=random.randint(0, 250000),
            zero_declare=ac.zero_declare,
        )
        t.profit = t.income - t.cost
        t.total_tax = 0 if ac.zero_declare else round(float(t.income) * 0.01, 2)
        t.save()
    # 本月任务（进行中）
    for ac in acc_clients:
        t = MonthlyTask.objects.create(
            client=ac, period=MONTH, accountant=ac.accountant,
            status=random.choices(["WAIT_DOC", "DOING", "DONE"], weights=[45, 40, 15])[0],
            deadline=date(2026, 10, 15),
            zero_declare=ac.zero_declare,
        )
    log(f"月度做账任务 {MonthlyTask.objects.count()} 条（{LAST_MONTH} + {MONTH}）")

    for i in range(8):
        BusinessItem.objects.create(
            client=random.choice(acc_clients),
            title=random.choice(["工商地址变更", "法人变更", "经营范围变更", "公司注销办理", "异常处理"]),
            item_type=random.choice(["CHANGE", "CANCEL", "ABNORMAL"]),
            status=random.choice(["PENDING", "PROCESSING", "DONE"]),
            handler=random.choice(acc_users),
            start_at=TODAY - timedelta(days=random.randint(1, 20)),
            progress=random.choice([0, 30, 60, 100]),
            fee=random.choice([500, 800, 1200, 2000]),
        )
    log(f"工商事项 {BusinessItem.objects.count()} 条")


def create_hr_reports(depts, users):
    print("\n[6/8] 考勤 / 请假 / 汇报")
    AttendanceRule.objects.create(name="标准考勤", work_start=dtime(9, 0), work_end=dtime(18, 0),
                                  late_minutes=10, late_penalty=20, absent_penalty=200,
                                  work_days="1,2,3,4,5,6", is_default=True)

    staff = list(User.objects.filter(status__in=["PROBATION", "REGULAR", "INTERN"]))
    for u in staff:
        for d in daterange(TODAY - timedelta(days=29), TODAY):
            if d.weekday() == 6:
                continue
            roll = random.random()
            if roll < 0.05:
                status = "LEAVE"
            elif roll < 0.08:
                status = "ABSENT"
            elif roll < 0.16:
                status = "LATE"
            else:
                status = "NORMAL"
            if status == "ABSENT":
                continue
            in_hour = 9 if status != "LATE" else random.choice([9, 9, 10])
            in_min = 0 if status != "LATE" else random.randint(11, 40)
            ci = timezone.make_aware(datetime.combine(d, dtime(in_hour, in_min)))
            co = timezone.make_aware(datetime.combine(d, dtime(random.randint(18, 20), random.randint(0, 59))))
            Attendance.objects.update_or_create(
                user=u, date=d,
                defaults=dict(check_in=ci, check_out=co,
                              status="LEAVE" if status == "LEAVE" else status,
                              late_minutes=in_min if status == "LATE" else 0,
                              work_hours=round((co - ci).total_seconds() / 3600 - 1.5, 2),
                              check_in_location="昆明市五华区XX大厦"))
    log(f"考勤记录 {Attendance.objects.count()} 条（近 30 天）")

    leave_types = ["PERSONAL", "SICK", "ANNUAL", "OFF"]
    for i in range(12):
        u = random.choice(staff)
        s = TODAY + timedelta(days=random.randint(-5, 10))
        LeaveApplication.objects.create(
            user=u, leave_type=random.choice(leave_types),
            start_at=timezone.make_aware(datetime.combine(s, dtime(9, 0))),
            end_at=timezone.make_aware(datetime.combine(s, dtime(18, 0))),
            days=1,
            reason=random.choice(["家里有事", "身体不适", "年假休息", "调休"]),
            status=random.choices(["PENDING", "APPROVED", "REJECTED"], weights=[50, 40, 10])[0],
        )
    log(f"请假申请 {LeaveApplication.objects.count()} 条（含待审批）")

    for u in staff:
        for d in daterange(TODAY - timedelta(days=14), TODAY):
            if d.weekday() == 6 or random.random() < 0.08:
                continue
            DailyReport.objects.update_or_create(
                user=u, date=d,
                defaults=dict(
                    today_done=random.choice([
                        "电话跟进新线索 60 通，加微 8 人，重点跟进 3 家意向客户。",
                        "完成 12 家客户的凭证录入，5 家完成纳税申报。",
                        "优化百度账户关键词，调整出价，今日消耗 780 元，留资 21 条。",
                        "处理工商变更 2 件，客户回访 8 家，催收资料 5 家。"]),
                    today_data={"calls": random.randint(30, 90),
                                "wechat": random.randint(2, 15),
                                "deal": random.randint(0, 2)},
                    problems=random.choice(["客户资料迟迟不给，影响做账进度", "百度账户线索质量下降",
                                            "部分客户电话打不通", "无"]),
                    tomorrow_plan="继续跟进高意向客户，重点催收 3 家资料",
                    status="SUBMITTED",
                    submitted_at=timezone.make_aware(datetime.combine(d, dtime(18, 30))),
                    score=random.randint(75, 98) if random.random() > 0.3 else None,
                ))
    log(f"工作日报 {DailyReport.objects.count()} 条（近 15 天）")

    for u in staff:
        MonthlyReport.objects.update_or_create(
            user=u, month=LAST_MONTH,
            defaults=dict(
                summary="本月整体达成情况良好，重点客户跟进到位。",
                performance=random.randint(20000, 80000),
                target=u.month_target or 30000,
                next_plan="下月重点提升转化率，加强老客户续费。",
                self_review="时间管理还需改进，电话量可以再提升。",
                submitted_at=timezone.make_aware(datetime(2026, 9, 1, 10, 0)),
                score=random.randint(70, 95),
            ))
    log(f"月度汇报 {MonthlyReport.objects.count()} 份")


def summary():
    print("\n" + "=" * 60)
    print("演示数据初始化完成")
    print("=" * 60)
    print(f"  员工        {User.objects.count()} 人")
    print(f"  部门        {Department.objects.filter(is_deleted=False).count()} 个")
    print(f"  企业文化    {CultureArticle.objects.count()} 篇")
    print(f"  公司制度    {Regulation.objects.count()} 项")
    print(f"  知识文章    {KnowledgeArticle.objects.count()} 篇")
    print(f"  考试题目    {Question.objects.count()} 道")
    print(f"  销售线索    {Lead.objects.count()} 条")
    print(f"  客户档案    {Customer.objects.count()} 家")
    print(f"  合同订单    {Contract.objects.count()} 份")
    print(f"  通话记录    {CallRecord.objects.count()} 条")
    print(f"  代账客户    {AccountingClient.objects.count()} 家")
    print(f"  做账任务    {MonthlyTask.objects.count()} 条")
    print(f"  投放数据    {AdDailyStat.objects.count()} 条")
    print(f"  考勤记录    {Attendance.objects.count()} 条")
    print(f"  工作日报    {DailyReport.objects.count()} 条")
    print("\n  登录账号：")
    print("    老板     boss     / admin123")
    print("    销售经理 sales_mgr / 123456")
    print("    会计经理 acc_mgr  / 123456")
    print("    运营经理 ops_mgr  / 123456")
    print("    人事     hr       / 123456")
    print("    普通员工 sales1   / 123456")
    print("=" * 60)


def main():
    print("=" * 60)
    print("财税企管云 · 演示数据初始化")
    print("=" * 60)
    if len(sys.argv) > 1 and sys.argv[1] == "reset":
        reset_data()
    elif User.objects.filter(is_superuser=False).exists():
        print("检测到已有业务数据，如需重建请执行：python seed_demo.py reset")
        summary()
        return
    depts, teams, users = create_org()
    create_onboarding()
    create_ops(users)
    create_sales(depts, teams, users)
    create_accounting(depts, users)
    create_hr_reports(depts, users)
    summary()


if __name__ == "__main__":
    main()
