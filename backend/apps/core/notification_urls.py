from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import NotificationViewSet, DeviceTokenViewSet

router = DefaultRouter()
router.register(r"", NotificationViewSet, basename="notification")
router.register(r"device", DeviceTokenViewSet, basename="device-token")

urlpatterns = [
    path("", include(router.urls)),
]
