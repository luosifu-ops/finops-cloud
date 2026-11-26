"""新增投放渠道：58同城

2026-11-04 Boss 指示：线索录入「来源平台」下拉增加 58同城。
渠道字典由 growth.LeadChannel 驱动，前端无需改动；本迁移幂等（update_or_create）。
"""
from django.db import migrations


def forwards(apps, schema_editor):
    LeadChannel = apps.get_model("growth", "LeadChannel")
    LeadChannel.objects.update_or_create(
        code="WUBA",
        defaults={
            "name": "58同城",
            "is_enabled": True,
            "is_reserved": False,
            "sort": 65,
            "is_deleted": False,
            "deleted_at": None,
        },
    )


def backwards(apps, schema_editor):
    LeadChannel = apps.get_model("growth", "LeadChannel")
    LeadChannel.objects.filter(code="WUBA").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("growth", "0009_alter_fieldtask_assignee_name_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
