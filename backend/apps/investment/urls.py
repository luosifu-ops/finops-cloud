from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import viewsets

router = DefaultRouter()
router.register("policies", viewsets.PolicyViewSet, basename="invest-policy")
router.register("materials", viewsets.MaterialViewSet, basename="invest-material")
router.register("inquiries", viewsets.InquiryViewSet, basename="invest-inquiry")

urlpatterns = [
    path("", include(router.urls)),
]
