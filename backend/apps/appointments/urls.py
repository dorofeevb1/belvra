from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AppointmentViewSet,
    AvailableSlotsView,
    ClientNoteViewSet,
    ClientStatsView,
    ManualCreateView,
    MyClientsView,
    ReviewViewSet,
    WorkScheduleViewSet,
)

router = DefaultRouter()
# Register schedules and reviews first to avoid conflicts with "" path
router.register("schedules", WorkScheduleViewSet, basename="schedule")
router.register("reviews", ReviewViewSet, basename="review")
router.register("client-notes", ClientNoteViewSet, basename="client-note")
router.register("", AppointmentViewSet, basename="appointment")

urlpatterns = [
    # available-slots must come before router to avoid conflict with "" path
    path("available-slots/", AvailableSlotsView.as_view(), name="available-slots"),
    path("client-stats/", ClientStatsView.as_view(), name="client-stats"),
    path("manual-create/", ManualCreateView.as_view(), name="manual-create"),
    path("my-clients/", MyClientsView.as_view(), name="my-clients"),
    path("", include(router.urls)),
]
