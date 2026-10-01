"""会计部演示数据播种（幂等）。

目的：确保「纳税申报」页面开箱即有数据，完整可用。
逻辑：
  1. 税种缺失时创建 5 个基础税种（无外键依赖，保证表单下拉有选项）。
  2. 仅当申报表为空时，基于现有月度做账任务生成申报演示数据；
     若会计部基础数据（客户 / 月度任务）因部署环境差异而缺失，则跳过并提示，
     不强行造数，避免与既有播种冲突。
可重复执行：已存在申报数据则直接跳过，绝不重复造数。
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date

from apps.accounting.models import (
    TaxType, AccountingClient, MonthlyTask, TaxDeclaration,
)


class Command(BaseCommand):
    help = "幂等播种会计部演示数据（基础税种 + 纳税申报），确保纳税申报页完整可用"

    def handle(self, *args, **options):
        # 1) 税种（缺失才创建，保证表单下拉有值）
        if not TaxType.objects.exists():
            for name, cycle, rule in [
                ("增值税", "MONTH", "次月15日前"),
                ("企业所得税", "QUARTER", "季后15日内"),
                ("个人所得税", "MONTH", "次月15日前"),
                ("附加税", "MONTH", "次月15日前"),
                ("印花税", "IRREGULAR", "按次申报"),
            ]:
                TaxType.objects.create(name=name, cycle=cycle, deadline_rule=rule, is_active=True)
            self.stdout.write(self.style.SUCCESS("已创建 5 个基础税种"))
        tax_types = list(TaxType.objects.filter(is_active=True)) or [TaxType.objects.first()]

        # 2) 申报记录（幂等）
        if TaxDeclaration.objects.exists():
            self.stdout.write(self.style.SUCCESS(
                f"已存在申报数据 {TaxDeclaration.objects.count()} 条，跳过播种"))
            return

        if not MonthlyTask.objects.exists():
            self.stdout.write(self.style.WARNING(
                "未检测到月度做账任务，无法生成申报记录；请先保证会计部基础数据已播种"))
            return

        status_pool = ["PENDING", "DECLARED", "PAID", "ZERO", "OVERDUE"]
        created = 0
        tasks = list(MonthlyTask.objects.filter(is_deleted=False)[:50])
        for i, task in enumerate(tasks):
            try:
                y, m = int(task.period[:4]), int(task.period[5:7])
                deadline = task.deadline or date(y, m, 15)
            except (ValueError, IndexError, TypeError):
                deadline = None
            tt = tax_types[i % len(tax_types)]
            TaxDeclaration.objects.create(
                task=task,
                tax_type=tt,
                period=task.period,
                deadline=deadline,
                amount=Decimal(f"{(i % 5) * 1234.56 + 500:.2f}"),
                paid_amount=Decimal("0.00"),
                status=status_pool[i % len(status_pool)],
                operator=task.accountant,
                remark="",
            )
            created += 1
            # 约半数任务再补一条「企业所得税」申报
            if i % 2 == 0:
                TaxDeclaration.objects.create(
                    task=task,
                    tax_type=tax_types[(i + 1) % len(tax_types)],
                    period=task.period,
                    deadline=deadline,
                    amount=Decimal(f"{(i % 3) * 888.0 + 200:.2f}"),
                    paid_amount=Decimal("0.00"),
                    status="PENDING",
                    operator=task.accountant,
                    remark="",
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f"已生成纳税申报演示数据 {created} 条"))
