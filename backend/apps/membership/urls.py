from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import viewsets
from .viewsets import PayView, pay_notify

router = DefaultRouter()
router.register("plans", viewsets.PlanViewSet, basename="membership-plan")
router.register("subscriptions", viewsets.SubscriptionViewSet, basename="membership-subscription")

urlpatterns = [
    path("", include(router.urls)),
    path("permissions/", viewsets.permissions_view, name="membership-permissions"),
    path("pay/", PayView.as_view(), name="membership-pay"),
    path("pay/notify/", pay_notify, name="membership-pay-notify"),
]
