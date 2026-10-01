from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import viewsets

router = DefaultRouter()
router.register("cultures", viewsets.CultureArticleViewSet, basename="culture-article")
router.register("regulations", viewsets.RegulationViewSet, basename="regulation")
router.register("knowledge-categories", viewsets.KnowledgeCategoryViewSet, basename="knowledge-category")
router.register("articles", viewsets.KnowledgeArticleViewSet, basename="knowledge-article")
router.register("question-banks", viewsets.QuestionBankViewSet, basename="question-bank")
router.register("questions", viewsets.QuestionViewSet, basename="question")
router.register("exams", viewsets.ExamViewSet, basename="exam")
router.register("profiles", viewsets.OnboardingProfileViewSet, basename="onboarding-profile")
router.register("tasks", viewsets.OnboardingTaskViewSet, basename="onboarding-task")

urlpatterns = [
    path("", include(router.urls)),
]
