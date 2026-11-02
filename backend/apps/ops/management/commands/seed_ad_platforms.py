"""播种投放平台字典（幂等）

2026-11-02 修复：生产 AdPlatform/AdAccount 字典为空 → 数据录入页手填「平台ID」必然失败。
"""
from django.core.management.base import BaseCommand

from apps.ops.models import AdPlatform

PLATFORMS = [
    ("DOUYIN", "抖音"), ("KUAISHOU", "快手"), ("XIAOHONGSHU", "小红书"),
    ("BAIDU", "百度推广"), ("AMAP", "高德地图"), ("WECHAT", "微信广告"),
    ("TENCENT", "腾讯广告"), ("OFFLINE", "线下地推"), ("OTHER", "其他"),
]


class Command(BaseCommand):
    help = "播种投放平台字典（幂等，已存在则跳过）"

    def handle(self, *args, **opts):
        created = 0
        for code, name in PLATFORMS:
            _, c = AdPlatform.objects.get_or_create(code=code, defaults={"name": name})
            created += int(c)
        self.stdout.write(self.style.SUCCESS(f"投放平台播种完成：新增 {created} 个，共 {AdPlatform.objects.count()} 个"))
