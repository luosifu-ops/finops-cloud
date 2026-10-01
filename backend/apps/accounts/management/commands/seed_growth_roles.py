"""增量演示账号播种：为 4 大新模块（线索录入 / 合同名录 / 外勤与增值 / 人事架构）补齐角色账号与增长中心职能角色。

设计原则：
  - 纯增量、幂等：仅「不存在时」创建账号，已存在则跳过；不会清空任何既有数据。
  - 仅用于 SQLite 预览 / 演示环境；生产（设置 DATABASE_URL）模式下 start.sh 不会调用本命令。
  - 默认密码统一为 demo123456，仅演示用。

覆盖角色：
  hr01      人事行政(HR)            -> 看得到「组织架构 / 入职审核」(isHR)
  ops01     运营(EMPLOYEE, dept=OPS, GrowthRole=OPS) -> 线索录入中心仅看自己录入；合同名录(运营部)
  closer01  成交师(GrowthRole=CLOSER) -> 线索工作台 / 公海领取
  field01   外勤(GrowthRole=FIELD)   -> 外勤任务池(仅自己被派的单)
  va01      增值专员(GrowthRole=VA_STAFF) -> 增值业务部(仅自己的项目)
  vamgr01   增值主管(LEADER, GrowthRole=VA_MANAGER, can_view_all) -> 增值业务部全部
此外为既有 closer1 补 GrowthRole=CLOSER，使其可用于增长中心线索流转走查。
"""
from django.core.management.base import BaseCommand
from apps.accounts.models import Department, User
from apps.growth.models import GrowthRole

PASSWORD = "demo123456"

# (username, name, role, dept_code, growth_role_or_None, dept_key, can_view_all)
NEW_ACCOUNTS = [
    ("hr01", "人事小美", "HR", "MGMT", None, "", False),
    ("ops01", "运营小绿", "EMPLOYEE", "OPS", "OPS", "OPS", False),
    ("closer01", "成交师小王", "EMPLOYEE", None, "CLOSER", "", False),
    ("field01", "外勤老李", "EMPLOYEE", None, "FIELD", "FIELD_WORK", False),
    ("va01", "增值小赵", "EMPLOYEE", None, "VA_STAFF", "VALUE_ADDED", False),
    ("vamgr01", "增值主管老钱", "LEADER", None, "VA_MANAGER", "VALUE_ADDED", True),
]

# 既有账号 -> 需要补的增长中心职能角色
EXISTING_GROWTH = {
    "closer1": ("CLOSER", "", False),
}


class Command(BaseCommand):
    help = "为 4 大新模块补齐演示角色账号（幂等，仅预览模式调用）"

    def handle(self, *args, **options):
        dept_cache = {d.code: d for d in Department.objects.all()}

        created = 0
        for un, name, role, dept_code, g_role, g_dept, g_all in NEW_ACCOUNTS:
            defaults = {
                "role": role,
                "department": dept_cache.get(dept_code) if dept_code else None,
            }
            user, was_created = User.objects.get_or_create(username=un, defaults=defaults)
            if not was_created:
                # 已存在：补齐缺失字段（不破坏既有数据）
                changed = False
                if user.role != role:
                    user.role = role
                    changed = True
                target_dept = dept_cache.get(dept_code) if dept_code else None
                if user.department_id != (target_dept.id if target_dept else None):
                    user.department = target_dept
                    changed = True
                if not user.check_password(PASSWORD):
                    user.set_password(PASSWORD)
                    changed = True
                if changed:
                    user.save()
            else:
                user.set_password(PASSWORD)
                user.save()
                created += 1

            if g_role:
                gr, gc = GrowthRole.objects.get_or_create(
                    user=user,
                    defaults={"role": g_role, "dept_key": g_dept, "can_view_all": g_all},
                )
                if not gc:
                    gr.role = g_role
                    gr.dept_key = g_dept
                    gr.can_view_all = g_all
                    gr.save()
            self.stdout.write(self.style.SUCCESS(
                f"  ✓ {un:10s} role={role:9s} dept={dept_code or '-':5s} "
                f"growth={'None' if not g_role else g_role}{' (can_view_all)' if g_all else ''}"
            ))

        for un, (g_role, g_dept, g_all) in EXISTING_GROWTH.items():
            try:
                user = User.objects.get(username=un)
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  - 跳过 {un}（不存在）"))
                continue
            gr, gc = GrowthRole.objects.get_or_create(
                user=user,
                defaults={"role": g_role, "dept_key": g_dept, "can_view_all": g_all},
            )
            if gc:
                self.stdout.write(self.style.SUCCESS(f"  ✓ 为既有 {un} 补 GrowthRole={g_role}"))
            else:
                self.stdout.write(self.style.WARNING(f"  - 既有 {un} 已有 GrowthRole={gr.role}（保持）"))

        self.stdout.write(self.style.SUCCESS(f"\n演示角色账号播种完成（新增 {created} 个账号）。密码统一：{PASSWORD}"))
