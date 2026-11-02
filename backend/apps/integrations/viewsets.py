"""对标账号库视图集（2026-11-02 Boss 指示）

全员可用：录入 / 检索 / 编辑 / 删除自己或他人的对标账号（对标库为公司公共资源）。
数据不按人隔离（Boss 需求是全公司共享对标情报），仅要求登录。
"""
from rest_framework import serializers, viewsets

from apps.common.permissions import is_authenticated_user
from .models import BenchmarkAccount
from .services import PLATFORM_LABELS


class BenchmarkAccountSerializer(serializers.ModelSerializer):
    platform_label = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source="created_by.first_name", read_only=True, default="")

    class Meta:
        model = BenchmarkAccount
        fields = [
            "id", "platform", "platform_label", "nickname", "account_id",
            "fans", "likes", "works", "avg_play", "tags", "sign", "url", "note",
            "created_by", "created_by_name", "created_at",
        ]
        read_only_fields = ["created_by", "created_at"]

    def get_platform_label(self, obj):
        return PLATFORM_LABELS.get(obj.platform, obj.platform)


class BenchmarkAccountViewSet(viewsets.ModelViewSet):
    """对标账号 CRUD（登录即可用，全公司共享）"""
    queryset = BenchmarkAccount.objects.filter(is_deleted=False)
    serializer_class = BenchmarkAccountSerializer
    search_fields = ["nickname", "account_id", "tags", "sign"]
    ordering_fields = ["fans", "likes", "works", "avg_play", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get("platform") and p["platform"] != "ALL":
            qs = qs.filter(platform=p["platform"])
        if p.get("q"):
            from django.db.models import Q
            q = p["q"].strip()
            qs = qs.filter(
                Q(nickname__icontains=q) | Q(account_id__icontains=q)
                | Q(tags__icontains=q) | Q(sign__icontains=q)
            )
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        if is_authenticated_user(user):
            serializer.save(created_by=user)
        else:
            serializer.save()
