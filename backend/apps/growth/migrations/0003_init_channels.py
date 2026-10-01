"""初始化投放渠道字典

启用：抖音 / 小红书 / 百度 / 高德 / 美团 / 闲鱼
预留扩展位（后续后台一键开启）：京东 / 淘宝 / 拼多多

纯新增数据，不触碰任何既有表与既有渠道定义（ops.AdPlatform / sales.Lead.SOURCE）。
"""
from django.db import migrations

# (code, name, enabled, reserved, sort)
CHANNELS = [
    ("DOUYIN", "抖音", True, False, 10),
    ("XIAOHONGSHU", "小红书", True, False, 20),
    ("BAIDU", "百度", True, False, 30),
    ("AMAP", "高德", True, False, 40),
    ("MEITUAN", "美团", True, False, 50),
    ("XIANYU", "闲鱼", True, False, 60),
    # 预留扩展位
    ("JD", "京东", False, True, 70),
    ("TAOBAO", "淘宝", False, True, 80),
    ("PDD", "拼多多", False, True, 90),
]


def forwards(apps, schema_editor):
    LeadChannel = apps.get_model("growth", "LeadChannel")
    for code, name, enabled, reserved, sort in CHANNELS:
        LeadChannel.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "is_enabled": enabled,
                "is_reserved": reserved,
                "sort": sort,
            },
        )


def backwards(apps, schema_editor):
    LeadChannel = apps.get_model("growth", "LeadChannel")
    LeadChannel.objects.filter(code__in=[c[0] for c in CHANNELS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("growth", "0002_growthrole"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
