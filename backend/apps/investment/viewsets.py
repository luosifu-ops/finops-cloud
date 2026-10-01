"""招商板块视图集"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.viewsets import ScopeModelViewSet
from .models import InvestPolicy, InvestMaterial, InvestInquiry
from .serializers import (
    InvestPolicySerializer, InvestMaterialSerializer, InvestInquirySerializer,
)


class PolicyViewSet(viewsets.ModelViewSet):
    queryset = InvestPolicy.objects.filter(is_deleted=False)
    serializer_class = InvestPolicySerializer

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()


class MaterialViewSet(viewsets.ModelViewSet):
    queryset = InvestMaterial.objects.filter(is_deleted=False)
    serializer_class = InvestMaterialSerializer

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()


class InquiryViewSet(ScopeModelViewSet):
    owner_field = "created_by"
    queryset = InvestInquiry.objects.filter(is_deleted=False)
    serializer_class = InvestInquirySerializer

    @action(detail=True, methods=["post"])
    def handle(self, request, pk=None):
        """修改咨询状态：body={status}"""
        obj = self.get_object()
        new_status = request.data.get("status")
        if new_status in dict(InvestInquiry.STATUS):
            obj.status = new_status
            obj.save(update_fields=["status"])
        return Response(InvestInquirySerializer(obj).data)
