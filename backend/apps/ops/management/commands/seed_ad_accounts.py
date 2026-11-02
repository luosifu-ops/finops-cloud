"""播种广告账户与推广计划字典（幂等）

2026-11-02 Boss 指示：数据录入页「账户/推广计划」下拉为空，先按 9 个投放平台
各建一个默认主账户 + 一个默认线索计划，保证录入可用；Boss 后续提供真实账户名
后可直接在页面编辑改名，不新增不覆盖。

幂等规则：某平台下已存在任何账户则整平台跳过（不重复播种、不动已有数据）。
"""
from django.core.management.base import BaseCommand

from apps.ops.models import AdAccount, AdCampaign, AdPlatform


class Command(BaseCommand):
    help = "播种广告账户与推广计划字典（幂等，平台下已有账户则跳过）"

    def handle(self, *args, **opts):
        created_accounts = 0
        created_campaigns = 0
        skipped = []
        for p in AdPlatform.objects.all().order_by("id"):
            if p.accounts.exists():
                skipped.append(p.name)
                continue
            acc = AdAccount.objects.create(platform=p, name=f"{p.name}-主账户", status="ACTIVE")
            created_accounts += 1
            AdCampaign.objects.create(account=acc, name=f"{p.name}-线索计划", goal="线索", status="ACTIVE")
            created_campaigns += 1
        self.stdout.write(self.style.SUCCESS(
            f"广告账户播种完成：新增账户 {created_accounts} 个、推广计划 {created_campaigns} 个；"
            f"已有账户跳过平台：{'、'.join(skipped) if skipped else '无'}"
        ))
