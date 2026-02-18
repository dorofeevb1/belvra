from django.db import transaction
from django.db.models import F
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from apps.core.permissions import IsAdminOrReadOnly, IsMasterOrReadOnly, IsMasterOwner

from .models import Category, MasterService, PortfolioItem, Service
from .serializers import (
    CategorySerializer,
    MasterServiceSerializer,
    MasterServiceCreateSerializer,
    PortfolioItemCreateSerializer,
    PortfolioItemSerializer,
    ServiceDetailSerializer,
    ServiceSerializer,
)


@extend_schema_view(
    list=extend_schema(tags=["Категории"], summary="Список категорий"),
    retrieve=extend_schema(tags=["Категории"], summary="Детали категории"),
    create=extend_schema(tags=["Категории"], summary="Создать категорию"),
    update=extend_schema(tags=["Категории"], summary="Обновить категорию"),
    partial_update=extend_schema(tags=["Категории"], summary="Частичное обновление категории"),
    destroy=extend_schema(tags=["Категории"], summary="Удалить категорию"),
)
class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for service categories."""

    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = "slug"
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["order", "name"]

    def get_permissions(self):
        if self.action in ["list", "retrieve", "services"]:
            return [AllowAny()]
        return [IsAdminUser()]

    @extend_schema(
        tags=["Категории"],
        summary="Услуги категории",
        description="Получение всех услуг в выбранной категории"
    )
    @action(detail=True, methods=["get"])
    def services(self, request, slug=None):
        """Get all services in a category."""
        category = self.get_object()
        services = Service.objects.filter(category=category, is_active=True)
        serializer = ServiceSerializer(services, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(tags=["Услуги"], summary="Список услуг"),
    retrieve=extend_schema(tags=["Услуги"], summary="Детали услуги"),
    create=extend_schema(tags=["Услуги"], summary="Создать услугу"),
    update=extend_schema(tags=["Услуги"], summary="Обновить услугу"),
    partial_update=extend_schema(tags=["Услуги"], summary="Частичное обновление услуги"),
    destroy=extend_schema(tags=["Услуги"], summary="Удалить услугу"),
)
class ServiceViewSet(viewsets.ModelViewSet):
    """ViewSet for services."""

    queryset = Service.objects.filter(is_active=True).select_related("category")
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category", "is_popular"]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "price", "duration"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ServiceDetailSerializer
        return ServiceSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve", "popular"]:
            return [AllowAny()]
        return [IsAdminUser()]

    @extend_schema(
        tags=["Услуги"],
        summary="Популярные услуги",
        description="Получение списка популярных услуг"
    )
    @action(detail=False, methods=["get"])
    def popular(self, request):
        """Get popular services."""
        services = self.get_queryset().filter(is_popular=True)[:10]
        serializer = ServiceSerializer(services, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(tags=["Услуги мастеров"], summary="Список услуг мастеров"),
    retrieve=extend_schema(tags=["Услуги мастеров"], summary="Детали услуги мастера"),
    create=extend_schema(tags=["Услуги мастеров"], summary="Добавить услугу мастеру"),
    update=extend_schema(tags=["Услуги мастеров"], summary="Обновить услугу мастера"),
    partial_update=extend_schema(tags=["Услуги мастеров"], summary="Частичное обновление"),
    destroy=extend_schema(tags=["Услуги мастеров"], summary="Удалить услугу мастера"),
)
class MasterServiceViewSet(viewsets.ModelViewSet):
    """ViewSet for master services."""

    queryset = MasterService.objects.select_related("master__user", "service")
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["master", "service"]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return MasterServiceCreateSerializer
        return MasterServiceSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        if self.action == "create":
            return [IsMasterOrReadOnly()]
        # For update/delete, check if user owns the object
        return [IsMasterOrReadOnly(), IsMasterOwner()]

    def get_queryset(self):
        queryset = super().get_queryset()
        # For my_services action, filter by current master
        if self.action == "my_services" and self.request.user.is_authenticated:
            if hasattr(self.request.user, 'master_profile'):
                return queryset.filter(master=self.request.user.master_profile)
        return queryset

    def perform_create(self, serializer):
        """Создание услуги с проверкой лимита подписки."""
        if not hasattr(self.request.user, 'master_profile'):
            raise PermissionDenied("User must have a master profile")

        master = self.request.user.master_profile

        with transaction.atomic():
            # Lock master row to prevent race conditions with concurrent requests
            master.__class__.objects.select_for_update().get(pk=master.pk)
            current_count = MasterService.objects.filter(master=master).count()

            # Проверяем лимит услуг по подписке
            subscription = getattr(master, 'subscription', None)
            if subscription and not subscription.can_add_service(current_count):
                raise PermissionDenied(
                    "Достигнут лимит услуг. Перейдите на PRO для добавления неограниченного количества услуг."
                )

            serializer.save(master=master)

    @extend_schema(
        tags=["Услуги мастеров"],
        summary="Мои услуги",
        description="Получение списка услуг текущего мастера"
    )
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def my_services(self, request):
        """Get current master's services."""
        if not hasattr(request.user, 'master_profile'):
            return Response(
                {"detail": "User is not a master"},
                status=status.HTTP_403_FORBIDDEN
            )
        queryset = self.get_queryset()
        serializer = MasterServiceSerializer(queryset, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(tags=["Портфолио"], summary="Список работ"),
    retrieve=extend_schema(tags=["Портфолио"], summary="Детали работы"),
    create=extend_schema(tags=["Портфолио"], summary="Добавить работу"),
    update=extend_schema(tags=["Портфолио"], summary="Обновить работу"),
    partial_update=extend_schema(tags=["Портфолио"], summary="Частичное обновление"),
    destroy=extend_schema(tags=["Портфолио"], summary="Удалить работу"),
)
class PortfolioItemViewSet(viewsets.ModelViewSet):
    """ViewSet for portfolio items."""

    queryset = PortfolioItem.objects.select_related("master__user", "service").filter(is_published=True)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["master", "service"]
    search_fields = ["title", "description", "hashtags"]
    ordering_fields = ["created_at", "likes_count"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return PortfolioItemCreateSerializer
        return PortfolioItemSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve", "by_master"]:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = PortfolioItem.objects.select_related("master__user", "service")
        # For authenticated master, show all their items (including unpublished)
        if self.request.user.is_authenticated and hasattr(self.request.user, "master_profile"):
            if self.action in ["my_portfolio", "update", "partial_update", "destroy"]:
                return queryset.filter(master=self.request.user.master_profile)
        # For public access, show only published items
        return queryset.filter(is_published=True)

    def perform_create(self, serializer):
        if not hasattr(self.request.user, "master_profile"):
            raise PermissionDenied("User must have a master profile")
        serializer.save(master=self.request.user.master_profile)

    def perform_update(self, serializer):
        # Ensure master can only update their own items
        instance = self.get_object()
        if instance.master != self.request.user.master_profile:
            raise PermissionDenied("You can only update your own portfolio items")
        serializer.save()

    def perform_destroy(self, instance):
        # Ensure master can only delete their own items
        if instance.master != self.request.user.master_profile:
            raise PermissionDenied("You can only delete your own portfolio items")
        instance.delete()

    @extend_schema(
        tags=["Портфолио"],
        summary="Моё портфолио",
        description="Получение списка работ текущего мастера"
    )
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def my_portfolio(self, request):
        """Get current master's portfolio items."""
        if not hasattr(request.user, "master_profile"):
            return Response(
                {"detail": "User is not a master"},
                status=status.HTTP_403_FORBIDDEN
            )
        queryset = self.get_queryset()
        serializer = PortfolioItemSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=["Портфолио"],
        summary="Портфолио мастера",
        description="Получение списка работ конкретного мастера"
    )
    @action(detail=False, methods=["get"], url_path="master/(?P<master_id>[^/.]+)")
    def by_master(self, request, master_id=None):
        """Get portfolio items for a specific master."""
        queryset = self.get_queryset().filter(master_id=master_id)
        serializer = PortfolioItemSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=["Портфолио"],
        summary="Лайкнуть работу",
        description="Добавить лайк к работе"
    )
    @action(detail=True, methods=["post"])
    def like(self, request, pk=None):
        """Like a portfolio item."""
        item = self.get_object()
        PortfolioItem.objects.filter(pk=item.pk).update(likes_count=F("likes_count") + 1)
        item.refresh_from_db(fields=["likes_count"])
        return Response({"likes_count": item.likes_count})
