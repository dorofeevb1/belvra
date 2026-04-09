from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AnalyticsView, ExpenseViewSet, GoalView

router = DefaultRouter()
router.register(r'expenses', ExpenseViewSet, basename='expense')

urlpatterns = [
    path('analytics/', AnalyticsView.as_view(), name='finance-analytics'),
    path('goal/', GoalView.as_view(), name='finance-goal'),
    path('', include(router.urls)),
]
