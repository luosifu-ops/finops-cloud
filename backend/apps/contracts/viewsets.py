"""合同订单名录：视图集（电销 / 运营 独立核算 + 多附件上传）"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import ContractRecord, ContractFile
from .serializers import (
    ContractRecordSerializer, ContractRecordCreateSerializer, ContractFileSerializer,
)
from .permissions import scope_contracts, is_manager


class ContractRecordViewSet(viewsets.ModelViewSet):
    """合同订单名录（电销 / 运营 独立入口，数据按部门隔离）"""
    queryset = ContractRecord.objects.filter(is_deleted=False).select_related("signer")
    serializer_class = ContractRecordSerializer
    search_fields = ["company_name", "credit_code", "service_content", "recv_account"]
    ordering_fields = ["created_at", "amount", "signed_date"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = scope_contracts(qs, self.request.user)
        p = self.request.query_params
        if p.get("dept"):
            qs = qs.filter(dept=p["dept"])
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(signer=self.request.user, created_by=self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return ContractRecordCreateSerializer
        return ContractRecordSerializer

    # ---------- 多附件上传（收款截图 / 合同扫描件 / PDF）----------
    @action(detail=True, methods=["post"])
    def upload_file(self, request, pk=None):
        """本地上传合同附件（multipart/form-data：file + file_type）"""
        rec = self.get_object()
        # 权限：签单人本人 / 部门同事（同 dept）/ 管理层
        if not (is_manager(request.user)
                or rec.signer_id == request.user.id
                or rec.dept == _user_dept_code(request.user)):
            return Response({"detail": "无权操作该合同"}, status=status.HTTP_403_FORBIDDEN)
        f = request.FILES.get("file")
        if not f:
            return Response({"detail": "未收到文件"}, status=status.HTTP_400_BAD_REQUEST)
        file_type = request.data.get("file_type", "PDF")
        cf = ContractFile.objects.create(
            record=rec, file_type=file_type, file=f, created_by=request.user)
        return Response(ContractFileSerializer(cf).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"])
    def delete_file(self, request, pk=None):
        rec = self.get_object()
        fid = request.query_params.get("file_id") or request.data.get("file_id")
        cf = rec.files.filter(id=fid).first()
        if not cf:
            return Response({"detail": "附件不存在"}, status=status.HTTP_404_NOT_FOUND)
        cf.file.delete(save=False)
        cf.delete()
        return Response({"detail": "已删除"})

    # ---------- 部门核算看板 ----------
    @action(detail=False, methods=["get"])
    def dept_summary(self, request):
        """按部门聚合：合同数 / 签单总额 / 已收 / 状态分布（独立核算）"""
        from django.db.models import Sum, Count
        qs = scope_contracts(ContractRecord.objects.filter(is_deleted=False), request.user)
        rows = []
        for dept in ("SALES", "OPS"):
            sub = qs.filter(dept=dept)
            if not is_manager(request.user) and dept not in (
                    _user_dept_code(request.user),):
                # 非管理层且非本部门，跳过不可见部门
                if _user_dept_code(request.user) != dept:
                    continue
            agg = sub.aggregate(total=Count("id"), amount=Sum("amount"))
            rows.append({
                "dept": dept,
                "dept_label": dict(ContractRecord.DEPT)[dept],
                "count": agg["total"] or 0,
                "amount": float(agg["amount"] or 0),
            })
        return Response({"rows": rows})


def _user_dept_code(user):
    if not getattr(user, "department_id", None):
        return None
    return getattr(user.department, "code", None) if user.department else None
