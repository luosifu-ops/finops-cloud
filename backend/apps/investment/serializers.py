from rest_framework import serializers
from .models import InvestPolicy, InvestMaterial, InvestInquiry


class InvestPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestPolicy
        fields = "__all__"


class InvestMaterialSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = InvestMaterial
        fields = "__all__"


class InvestInquirySerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = InvestInquiry
        fields = "__all__"
        read_only_fields = ["created_by"]
