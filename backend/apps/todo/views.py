from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import TodoItem
from .serializers import (
    TodoItemCreateSerializer,
    TodoItemSerializer,
    TodoItemStatusUpdateSerializer,
)


@extend_schema_view(
    list=extend_schema(tags=["Задачи"], summary="Список задач"),
    retrieve=extend_schema(tags=["Задачи"], summary="Детали задачи"),
    create=extend_schema(tags=["Задачи"], summary="Создать задачу"),
    update=extend_schema(tags=["Задачи"], summary="Обновить задачу"),
    partial_update=extend_schema(tags=["Задачи"], summary="Частичное обновление задачи"),
    destroy=extend_schema(tags=["Задачи"], summary="Удалить задачу"),
)
class TodoItemViewSet(viewsets.ModelViewSet):
    """ViewSet for todo items."""

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "priority", "date"]
    search_fields = ["title", "description"]
    ordering_fields = ["date", "priority", "created_at"]
    ordering = ["-date", "-created_at"]

    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, "master_profile"):
            return TodoItem.objects.none()
        return TodoItem.objects.filter(master=user.master_profile)

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return TodoItemCreateSerializer
        if self.action == "update_status":
            return TodoItemStatusUpdateSerializer
        return TodoItemSerializer

    def perform_create(self, serializer):
        if not hasattr(self.request.user, "master_profile"):
            raise PermissionDenied("Только мастер может создавать задачи")
        serializer.save(master=self.request.user.master_profile)

    @extend_schema(
        tags=["Задачи"],
        summary="Задачи на дату",
        description="Получение списка задач на конкретную дату"
    )
    @action(detail=False, methods=["get"], url_path="by-date/(?P<date>[0-9-]+)")
    def by_date(self, request, date=None):
        """Get todos for a specific date."""
        queryset = self.get_queryset().filter(date=date)
        serializer = TodoItemSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=["Задачи"],
        summary="Сегодняшние задачи",
        description="Получение списка задач на сегодня"
    )
    @action(detail=False, methods=["get"])
    def today(self, request):
        """Get today's todos."""
        today = timezone.localdate()
        queryset = self.get_queryset().filter(date=today)
        serializer = TodoItemSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=["Задачи"],
        summary="Обновить статус задачи",
        request=TodoItemStatusUpdateSerializer
    )
    @action(detail=True, methods=["post"])
    def update_status(self, request, pk=None):
        """Update todo status."""
        todo = self.get_object()
        serializer = TodoItemStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        todo.status = serializer.validated_data["status"]
        todo.save(update_fields=["status", "updated_at"])

        return Response(TodoItemSerializer(todo).data)

    @extend_schema(
        tags=["Задачи"],
        summary="Статистика задач",
        description="Получение статистики по задачам"
    )
    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get todo statistics."""
        queryset = self.get_queryset()
        today = timezone.localdate()

        return Response({
            "total": queryset.count(),
            "todo": queryset.filter(status=TodoItem.Status.TODO).count(),
            "in_progress": queryset.filter(status=TodoItem.Status.IN_PROGRESS).count(),
            "done": queryset.filter(status=TodoItem.Status.DONE).count(),
            "today_total": queryset.filter(date=today).count(),
            "today_done": queryset.filter(date=today, status=TodoItem.Status.DONE).count(),
            "overdue": queryset.filter(date__lt=today).exclude(status=TodoItem.Status.DONE).count(),
        })
