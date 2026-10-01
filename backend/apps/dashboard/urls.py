from django.urls import path
from . import viewsets

urlpatterns = [
    path("overview/", viewsets.overview, name="dash-overview"),
    path("rank/", viewsets.rank, name="dash-rank"),
    path("trend/", viewsets.trend, name="dash-trend"),
    path("todo/", viewsets.todo, name="dash-todo"),
    path("department/<str:code>/", viewsets.department_detail, name="dash-dept"),
    path("department/<str:code>/members/", viewsets.department_members, name="dash-dept-members"),
    path("data-wall/", viewsets.data_wall, name="dash-data-wall"),
    path("company-performance/", viewsets.company_performance, name="dash-company-performance"),
    path("ai/chat/", viewsets.ai_chat, name="ai-chat"),
]
