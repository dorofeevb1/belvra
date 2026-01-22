from django.core.cache import cache
from django.db import connection
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification, DeviceToken
from .serializers import NotificationMarkReadSerializer, NotificationSerializer, DeviceTokenSerializer


class HealthCheckView(APIView):
    """Health check endpoint for load balancers and monitoring."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        health_status = {
            "status": "healthy",
            "database": self._check_database(),
            "cache": self._check_cache(),
        }

        if not all([health_status["database"], health_status["cache"]]):
            health_status["status"] = "unhealthy"
            return Response(health_status, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(health_status)

    def _check_database(self):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True
        except Exception:
            return False

    def _check_cache(self):
        try:
            cache.set("health_check", "ok", 1)
            return cache.get("health_check") == "ok"
        except Exception:
            return False


@extend_schema_view(
    list=extend_schema(
        tags=["Уведомления"],
        summary="Список уведомлений",
        description="Получение списка уведомлений текущего пользователя"
    ),
    retrieve=extend_schema(
        tags=["Уведомления"],
        summary="Детали уведомления",
        description="Получение деталей конкретного уведомления"
    ),
    destroy=extend_schema(
        tags=["Уведомления"],
        summary="Удалить уведомление",
        description="Удаление уведомления"
    ),
)
class NotificationViewSet(viewsets.ModelViewSet):
    """ViewSet for notifications."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "delete", "post"]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @extend_schema(
        tags=["Уведомления"],
        summary="Количество непрочитанных",
        description="Получение количества непрочитанных уведомлений"
    )
    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        """Get count of unread notifications."""
        count = self.get_queryset().filter(is_read=False).count()
        return Response({"count": count})

    @extend_schema(
        tags=["Уведомления"],
        summary="Отметить прочитанными",
        description="Отметить уведомления как прочитанные",
        request=NotificationMarkReadSerializer
    )
    @action(detail=False, methods=["post"])
    def mark_read(self, request):
        """Mark notifications as read."""
        serializer = NotificationMarkReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        notification_ids = serializer.validated_data.get("notification_ids", [])

        queryset = self.get_queryset().filter(is_read=False)

        if notification_ids:
            queryset = queryset.filter(id__in=notification_ids)

        updated = queryset.update(is_read=True, read_at=timezone.now())

        return Response({
            "detail": f"Отмечено прочитанными: {updated}",
            "count": updated
        })

    @extend_schema(
        tags=["Уведомления"],
        summary="Отметить одно прочитанным",
        description="Отметить конкретное уведомление как прочитанное"
    )
    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        """Mark single notification as read."""
        notification = self.get_object()
        notification.mark_as_read()
        return Response(NotificationSerializer(notification).data)

    @extend_schema(
        tags=["Уведомления"],
        summary="Удалить все прочитанные",
        description="Удалить все прочитанные уведомления"
    )
    @action(detail=False, methods=["delete"])
    def clear_read(self, request):
        """Delete all read notifications."""
        deleted, _ = self.get_queryset().filter(is_read=True).delete()
        return Response({
            "detail": f"Удалено уведомлений: {deleted}",
            "count": deleted
        })


@extend_schema_view(
    list=extend_schema(
        tags=["Push-уведомления"],
        summary="Список устройств",
        description="Получение списка зарегистрированных устройств для push-уведомлений"
    ),
    create=extend_schema(
        tags=["Push-уведомления"],
        summary="Регистрация устройства",
        description="Регистрация токена устройства для push-уведомлений"
    ),
    destroy=extend_schema(
        tags=["Push-уведомления"],
        summary="Удаление устройства",
        description="Удаление (деактивация) токена устройства"
    ),
)
class DeviceTokenViewSet(viewsets.ModelViewSet):
    """ViewSet for device push notification tokens."""

    serializer_class = DeviceTokenSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "delete"]
    lookup_field = "token"

    def get_queryset(self):
        return DeviceToken.objects.filter(user=self.request.user, is_active=True)

    def perform_destroy(self, instance):
        """Deactivate token instead of deleting."""
        instance.deactivate()

    @extend_schema(
        tags=["Push-уведомления"],
        summary="Деактивировать все устройства",
        description="Деактивировать все токены устройств пользователя"
    )
    @action(detail=False, methods=["post"])
    def deactivate_all(self, request):
        """Deactivate all device tokens for user."""
        count = self.get_queryset().update(is_active=False)
        return Response({
            "detail": f"Деактивировано устройств: {count}",
            "count": count
        })
