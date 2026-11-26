# -*- coding: utf-8 -*-
"""2026-11-23 Boss 指示：投放总览按「抖音素材 / 抖音直播 / 闲鱼」拆分。

平台字典幂等对齐：
  - 「抖音短视频」(存量无 code) → 更名「抖音素材」，code=DOUYIN_MATERIAL
  - 「抖音直播」 → code=DOUYIN_LIVE（后端兼容旧 DOUYIN）
  - 不存在则新建对应平台
所有操作幂等，可重复执行。
"""
from django.db import migrations


def align_platforms(apps, schema_editor):
    AdPlatform = apps.get_model("ops", "AdPlatform")

    def ensure(name, code, old_names=()):
        # 1) 先按 code 找
        obj = AdPlatform.objects.filter(code=code).first()
        # 2) 再按名称找（含历史名）
        if not obj:
            for nm in (name,) + tuple(old_names):
                obj = AdPlatform.objects.filter(name=nm).first()
                if obj:
                    break
        # 3) 都没有则新建
        if not obj:
            AdPlatform.objects.create(name=name, code=code)
            return
        # 对齐名称与 code（code 需判空避免 unique 冲突）
        changed = False
        if obj.name != name:
            obj.name = name
            changed = True
        if obj.code != code:
            dup = AdPlatform.objects.filter(code=code).exclude(pk=obj.pk).first()
            if not dup:
                obj.code = code
                changed = True
        if changed:
            obj.save()

    # 抖音素材：存量「抖音短视频」平滑更名，历史数据自动归入
    ensure("抖音素材", "DOUYIN_MATERIAL", old_names=("抖音短视频",))
    # 抖音直播
    ensure("抖音直播", "DOUYIN_LIVE", old_names=())
    # 闲鱼
    ensure("闲鱼", "XIANYU", old_names=())


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('ops', '0006_addailystat_cost_input'),
    ]

    operations = [
        migrations.RunPython(align_platforms, noop),
    ]
