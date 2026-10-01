# -*- coding: utf-8 -*-
"""按钉钉组织架构图初始化/修正公司部门树。

结构（与 boss 提供图片一致）：
  云南财税通集团有限公司
  ├── 销售部
  │   ├── 销售一部
  │   └── 销售二部
  ├── 会计部
  ├── 行政人事部
  └── 运营部
      ├── 主播
      ├── 运营
      └── 咨询
  └── 总经办

原则：
  - 幂等：按 code 查找，存在则更新名称/上级/编码，不存在则创建。
  - 仅预览模式（start.sh 无 DATABASE_URL 时）调用，生产模式不污染真实数据。
  - 不删不改现有用户，仅维护 Department 树；主管可后续在「组织架构」页编辑。
"""
from django.core.management.base import BaseCommand
from apps.accounts.models import Department

# (code, name, parent_code, description)
DEPARTMENTS = [
    # 一级部门
    ("ROOT", "云南财税通集团有限公司", None, "集团总部"),
    ("SALES", "销售部", "ROOT", "负责线索转化、客户签约、回款跟进"),
    ("ACCOUNT", "会计部", "ROOT", "负责代理记账、纳税申报、工商事项办理"),
    ("HR_DEPT", "行政人事部", "ROOT", "负责人事、行政、考勤、薪酬、绩效、组织架构"),
    ("OPS", "运营部", "ROOT", "负责各平台投放获客、内容运营、引流转化"),
    ("MGMT", "总经办", "ROOT", "公司整体经营与决策"),
    # 销售部子部门
    ("SALES1", "销售一部", "SALES", "销售一部"),
    ("SALES2", "销售二部", "SALES", "销售二部"),
    # 运营部子部门
    ("OPS_ANCHOR", "主播", "OPS", "直播运营 / 主播团队"),
    ("OPS_OPS", "运营", "OPS", "新媒体/内容/投放运营"),
    ("OPS_CONSULT", "咨询", "OPS", "客户咨询 / 售前客服"),
]


class Command(BaseCommand):
    help = "按钉钉架构图初始化/修正公司组织架构（幂等）"

    def handle(self, *args, **options):
        cache = {}
        created = 0
        updated = 0

        # 第一遍：确保所有部门记录存在
        for code, name, parent_code, description in DEPARTMENTS:
            dept, was_created = Department.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": description or "",
                    "parent_id": None,
                },
            )
            cache[code] = dept
            if was_created:
                created += 1
            else:
                # 名称/描述与图片不一致时修正
                changed = False
                if dept.name != name:
                    dept.name = name
                    changed = True
                if dept.description != (description or ""):
                    dept.description = description or ""
                    changed = True
                if changed:
                    dept.save()
                    updated += 1

        # 第二遍：绑定上级（此时所有记录已在 cache 中）
        for code, name, parent_code, description in DEPARTMENTS:
            dept = cache[code]
            target_parent = cache.get(parent_code) if parent_code else None
            if dept.parent_id != (target_parent.id if target_parent else None):
                dept.parent = target_parent
                dept.save()
                if code not in [d[0] for d in DEPARTMENTS[:6]]:  # 子部门才计更新
                    updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"组织架构树已同步：新增 {created} 个部门，更新 {updated} 个部门"
        ))
        self.stdout.write(self.style.SUCCESS(
            "当前部门树：云南财税通集团有限公司 → 销售部/会计部/行政人事部/运营部/总经办"
        ))
