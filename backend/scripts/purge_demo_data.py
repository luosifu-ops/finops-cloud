# -*- coding: utf-8 -*-
"""演示数据清理脚本（2026-10-30 Boss 指示：删除系统内所有演示数据 / 测试线索）

保留：
  - 全部员工账号（accounts.User）与部门 / 小组 / 岗位组织架构
  - 基础字典与配置（渠道、税种、平台、提成规则、考勤规则、会员套餐、题库、制度/知识/企业文化、入职任务、系统配置）
删除：
  - 全部业务演示数据（线索、客户、合同、通话记录、做账、申报、投放、外勤、公海、跟进等）
  - 全部演示产生的汇报、考勤、请假、审批、考试记录、站内信、操作日志

用法：venv/bin/python scripts/purge_demo_data.py [--dry-run]
"""
import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import transaction  # noqa: E402

# 按依赖顺序：先删子表 / 引用方，再删被引用方
PURGE_ORDER = [
    # 增长中心 / 外勤
    ("growth", "LeadFollowUp"), ("growth", "LeadStageLog"), ("growth", "LeadPool"),
    ("growth", "LeadFlow"), ("growth", "LeadExt"),
    ("growth", "FieldTaskNode"), ("growth", "FieldProgress"), ("growth", "FieldTask"),
    ("growth", "ValueAddedProject"), ("growth", "AdSpendRecord"), ("growth", "CloserChannel"),
    # 销售
    ("sales", "CallRecord"), ("sales", "Contract"), ("sales", "Customer"),
    ("sales", "Lead"), ("sales", "SalaryRecord"), ("sales", "SalesTarget"),
    # 会计
    ("accounting", "TaxDeclaration"), ("accounting", "MonthlyTask"),
    ("accounting", "BusinessItem"), ("accounting", "AnnualReport"), ("accounting", "AccountingClient"),
    # 运营投放
    ("ops", "AdDailyStat"), ("ops", "AdCampaign"), ("ops", "AdAccount"),
    ("ops", "ChannelBudget"), ("ops", "ContentPost"),
    # 汇报
    ("reports", "DailyReport"), ("reports", "WeeklyReport"),
    ("reports", "MonthlyReport"), ("reports", "TeamSummary"),
    # 人事
    ("hr", "ApprovalStep"), ("hr", "Approval"), ("hr", "LeaveApplication"), ("hr", "Attendance"),
    # 考试记录（题库 / 制度 / 知识保留）
    ("onboarding", "ExamRecord"), ("onboarding", "Exam"),
    # 招商咨询 / 会员订阅（政策与套餐内容保留）
    ("investment", "InvestInquiry"), ("membership", "Subscription"),
    # 全局：站内信 / 操作日志 / 短信验证码
    ("common", "InboxMessage"), ("common", "OperationLog"), ("accounts", "PhoneVerifyCode"),
]


def main():
    dry = "--dry-run" in sys.argv
    total = 0
    with transaction.atomic():
        for app, model in PURGE_ORDER:
            try:
                from django.apps import apps as dj_apps
                m = dj_apps.get_model(app, model)
            except Exception:
                continue
            n = m.objects.count()
            if not n:
                continue
            print(f"  清理 {app}.{model}: {n} 条")
            if not dry:
                m.objects.all().delete()
            total += n
    print(f"{'[dry-run] ' if dry else ''}共清理 {total} 条演示数据")
    print("保留：员工账号 / 组织架构 / 基础字典 / 题库与制度知识 / 系统配置")


if __name__ == "__main__":
    main()
