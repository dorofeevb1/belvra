from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AppointmentViewSet,
    AvailableSlotsView,
    ReviewViewSet,
    WorkScheduleViewSet,
)

router = DefaultRouter()
# Register schedules and reviews first to avoid conflicts with "" path
router.register("schedules", WorkScheduleViewSet, basename="schedule")
router.register("reviews", ReviewViewSet, basename="review")
router.register("", AppointmentViewSet, basename="appointment")

urlpatterns = [
    # available-slots must come before router to avoid conflict with "" path
    path("available-slots/", AvailableSlotsView.as_view(), name="available-slots"),
    path("", include(router.urls)),
]
