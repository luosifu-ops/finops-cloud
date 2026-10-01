from rest_framework import serializers
from .models import MembershipPlan, Subscription


class MembershipPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = MembershipPlan
        fields = "__all__"


class SubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    plan_code = serializers.CharField(source="plan.code", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Subscription
        fields = "__all__"
        read_only_fields = ["created_by"]
