"""公司通知公告：序列化器"""
from rest_framework import serializers

from .models import Announcement


class AnnouncementSerializer(serializers.ModelSerializer):
    """通知公告：发布人、类型中文、附件地址、已读人数与当前用户是否已读"""
    publisher_name = serializers.CharField(source="created_by.display_name", read_only=True)
    category_name = serializers.CharField(source="get_category_display", read_only=True)
    file_url = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()
    read_count = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()

    def get_file_url(self, obj):
        try:
            return obj.file.url if obj.file else ""
        except ValueError:
            return ""

    def get_file_size(self, obj):
        try:
            return obj.file.size if obj.file else 0
        except ValueError:
            return 0

    def get_read_count(self, obj):
        return obj.read_by.count()

    def get_is_read(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.read_by.filter(id=request.user.id).exists()
        return False

    class Meta:
        model = Announcement
        fields = [
            "id", "title", "content", "category", "category_name",
            "file", "file_name", "file_url", "file_size",
            "pinned", "read_count", "is_read",
            "publisher_name", "created_at", "updated_at",
        ]
        read_only_fields = [
            "created_at", "updated_at", "file", "file_url", "file_size",
            "read_count", "is_read", "publisher_name",
        ]
