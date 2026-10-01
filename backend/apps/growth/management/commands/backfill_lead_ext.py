"""一次性回填：为没有 LeadExt 的 sales.Lead 补建扩展记录。

目的：把「运营部老线索池（sales.Lead）」与「增长中心线索池（LeadExt）」真正打通为
       一个统一池。原运营部 120+ 条历史线索此前只有 sales.Lead、没有 LeadExt，
       若直接把运营部菜单指向增长中心工作台会丢失这些历史数据；本命令为其补建
       LeadExt（ops_owner 继承原 owner），既不删除任何历史字段，又让统一池完整。

特性：
  - 幂等：已存在 LeadExt 的线索自动跳过。
  - 仅新增，不修改任何既有 sales.Lead / LeadExt 记录。
  - 默认渠道：优先取第一个启用渠道；没有则创建「其他/历史线索」预留渠道。
"""
from django.core.management.base import BaseCommand
from apps.sales.models import Lead
from apps.growth.models import LeadExt, LeadChannel


class Command(BaseCommand):
    help = "为孤儿 sales.Lead 补建 LeadExt，打通运营部与增长中心线索池（幂等）"

    def handle(self, *args, **options):
        channel = LeadChannel.objects.filter(is_enabled=True).order_by("id").first()
        if channel is None:
            channel = LeadChannel.objects.create(
                code="OTHER", name="其他/历史线索", is_enabled=True,
                is_reserved=True, sort=999)
            self.stdout.write(self.style.WARNING(f"未找到启用渠道，已创建默认渠道：{channel.name}"))

        created = 0
        # 仅处理「尚未关联 LeadExt」的线索（反向 OneToOne：growth_ext__isnull=True）
        for lead in Lead.objects.filter(growth_ext__isnull=True).select_related("owner", "created_by"):
            ext = LeadExt.objects.create(
                lead=lead,
                channel=channel,
                source_account_no=(lead.source_detail or f"历史线索#{lead.id}")[:100],
                contact_type="WECHAT" if lead.wechat else "PHONE",
                contact_value=(lead.wechat or lead.phone or "")[:100],
                ops_owner=lead.owner,
                closer=None,
                in_pool=False,
                customer_need=lead.intention or "",
                contact_person=lead.name or "",
                acquisition_cost=0,
                deal_amount=0,
                created_by=lead.owner or lead.created_by,
            )
            created += 1
            self.stdout.write(f"  + LeadExt#{ext.id} <- Lead#{lead.id} (ops_owner={getattr(lead.owner, 'username', None)})")

        self.stdout.write(self.style.SUCCESS(f"回填完成：新增 LeadExt {created} 条，统一线索池已打通"))
