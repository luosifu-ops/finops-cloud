"""公司通知公告：视图集"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.permissions import IsManagerOrAbove
from .models import Announcement
from .serializers import AnnouncementSerializer


class AnnouncementViewSet(viewsets.ModelViewSet):
    """通知公告：全员可见、可接收（已读回执）；发布/编辑/删除仅管理层(BOSS/MANAGER)"""
    queryset = Announcement.objects.filter(is_deleted=False)
    serializer_class = AnnouncementSerializer
    search_fields = ["title", "content"]
    ordering_fields = ["created_at", "pinned"]

    def get_permissions(self):
        # 写操作（含附件上传）仅管理层；读操作任何登录用户
        if self.action in ("create", "update", "partial_update", "destroy", "upload_file"):
            return [IsManagerOrAbove()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def upload_file(self, request, pk=None):
        """上传/替换附件文件（单文件，≤20MB）"""
        ann = self.get_object()
        f = request.FILES.get("file")
        if not f:
            return Response({"code": 1, "msg": "未接收到文件"}, status=status.HTTP_400_BAD_REQUEST)
        if f.size and f.size > 20 * 1024 * 1024:
            return Response({"code": 1, "msg": "文件不能超过 20MB"}, status=status.HTTP_400_BAD_REQUEST)
        ann.file.save(f.name, f, save=True)
        ann.file_name = f.name
        ann.save(update_fields=["file_name"])
        return Response({"code": 0, "msg": "ok",
                         "data": AnnouncementSerializer(ann, context={"request": request}).data})

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        """当前用户标记已读（接收确认回执）"""
        ann = self.get_object()
        ann.read_by.add(request.user)
        return Response({"code": 0, "msg": "ok",
                         "data": {"is_read": True, "read_count": ann.read_by.count()}})

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        """当前用户未读数量（用于顶部提醒角标）"""
        user = request.user
        total = self.get_queryset().count()
        read = self.get_queryset().filter(read_by=user).count()
        return Response({"code": 0, "msg": "ok",
                         "data": {"unread": max(total - read, 0), "total": total}})
