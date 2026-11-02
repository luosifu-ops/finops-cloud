"""回填员工编号（工号）：给历史员工自动补 EMP0001 起的编号

背景：User.employee_no 字段早已存在（工号，唯一），但历史数据全部为空，
导致「员工管理」列表工号列大面积空白。业务侧要求新增员工自动生成编号，
存量员工同样需要补齐，否则列表仍显示空。

生成规则与 models.User.next_employee_no 保持一致：EMP + 4 位序号，按 id 升序。
"""
from django.db import migrations

PREFIX = "EMP"


def backfill(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    used = set()
    for no in User.objects.exclude(employee_no__isnull=True).values_list(
            "employee_no", flat=True):
        if no:
            used.add(no)
    seq = 0
    for user in User.objects.order_by("id").iterator():
        if user.employee_no:
            continue
        while True:
            seq += 1
            candidate = f"{PREFIX}{seq:04d}"
            if candidate not in used:
                break
        user.employee_no = candidate
        user.save(update_fields=["employee_no"])
        used.add(candidate)


def noop(apps, schema_editor):
    """回滚不清理工号：编号属于业务数据，回滚代码不应破坏已有编号。"""


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0011_entryapplication_password_hash"),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
