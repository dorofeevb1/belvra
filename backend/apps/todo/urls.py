from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TodoItemViewSet

router = DefaultRouter()
router.register("", TodoItemViewSet, basename="todo")

urlpatterns = [
    path("", include(router.urls)),
]
