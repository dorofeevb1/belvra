from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.core.notifications import NotificationService
from apps.core.tasks import (
    send_appointment_cancelled_task,
    send_appointment_confirmation_task,
    send_new_appointment_to_master_task,
    send_review_notification_task,
)
from apps.services.models import MasterService
from apps.users.models import MasterProfile

from .models import Appointment, Review, WorkSchedule
from .serializers import (
    AppointmentCancelSerializer,
    AppointmentCreateSerializer,
    AppointmentRescheduleSerializer,
    AppointmentSerializer,
    AvailableSlotsSerializer,
    ReviewSerializer,
    WorkScheduleSerializer,
)


@extend_schema_view(
    list=extend_schema(tags=["Расписание"], summary="Список расписаний"),
    retrieve=extend_schema(tags=["Расписание"], summary="Детали расписания"),
    create=extend_schema(tags=["Расписание"], summary="Создать расписание"),
    update=extend_schema(tags=["Расписание"], summary="Обновить расписание"),
    partial_update=extend_schema(tags=["Расписание"], summary="Частичное обновление"),
    destroy=extend_schema(tags=["Расписание"], summary="Удалить расписание"),
)
class WorkScheduleViewSet(viewsets.ModelViewSet):
    """ViewSet for work schedules."""

    serializer_class = WorkScheduleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["master", "weekday"]

    def get_queryset(self):
        if self.request.user.is_staff:
            return WorkSchedule.objects.all()
        if hasattr(self.request.user, "master_profile"):
            return WorkSchedule.objects.filter(master=self.request.user.master_profile)
        return WorkSchedule.objects.none()

    def perform_create(self, serializer):
        """Automatically set the master from the current user."""
        if hasattr(self.request.user, "master_profile"):
            serializer.save(master=self.request.user.master_profile)
        else:
            serializer.save()

    @extend_schema(
        tags=["Расписание"],
        summary="Массовое обновление расписания",
        description="Создание или обновление расписания для нескольких дней"
    )
    @action(detail=False, methods=["post"])
    def bulk(self, request):
        """Bulk create or update schedules for multiple days."""
        if not hasattr(request.user, "master_profile"):
            return Response(
                {"detail": "User must be a master"},
                status=status.HTTP_403_FORBIDDEN
            )

        master = request.user.master_profile
        schedules_data = request.data.get("schedules", [])

        if not schedules_data:
            return Response(
                {"detail": "No schedules provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        results = []
        for schedule_data in schedules_data:
            weekday = schedule_data.get("weekday")
            if weekday is None:
                continue

            # Try to find existing schedule for this weekday
            existing = WorkSchedule.objects.filter(
                master=master,
                weekday=weekday
            ).first()

            if existing:
                # Update existing schedule
                serializer = WorkScheduleSerializer(
                    existing,
                    data=schedule_data,
                    partial=True
                )
            else:
                # Create new schedule
                serializer = WorkScheduleSerializer(data=schedule_data)

            if serializer.is_valid():
                serializer.save(master=master)
                results.append(serializer.data)
            else:
                # Skip invalid entries but log errors
                results.append({
                    "weekday": weekday,
                    "error": serializer.errors
                })

        return Response({"schedules": results})


@extend_schema_view(
    list=extend_schema(tags=["Записи"], summary="Список записей"),
    retrieve=extend_schema(tags=["Записи"], summary="Детали записи"),
    create=extend_schema(tags=["Записи"], summary="Создать запись"),
    update=extend_schema(tags=["Записи"], summary="Обновить запись"),
    partial_update=extend_schema(tags=["Записи"], summary="Частичное обновление записи"),
    destroy=extend_schema(tags=["Записи"], summary="Удалить запись"),
)
class AppointmentViewSet(viewsets.ModelViewSet):
    """ViewSet for appointments."""

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "date", "master"]
    ordering_fields = ["date", "start_time", "created_at"]
    ordering = ["-date", "-start_time"]

    def get_queryset(self):
        user = self.request.user
        queryset = Appointment.objects.select_related(
            "client", "master__user", "service"
        ).filter(is_archived=False)

        if user.is_staff:
            return queryset

        if hasattr(user, "master_profile"):
            return queryset.filter(
                Q(client=user) | Q(master=user.master_profile)
            )

        return queryset.filter(client=user)

    def get_serializer_class(self):
        if self.action == "create":
            return AppointmentCreateSerializer
        return AppointmentSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        """Create appointment and send email to master."""
        appointment = serializer.save()

        # Send email notification to master
        master = appointment.master
        client = appointment.client
        # Get service name from master_service (for custom) or service (for catalog)
        if appointment.master_service:
            service_name = appointment.master_service.name
        elif appointment.service:
            service_name = appointment.service.name
        else:
            service_name = "Услуга"
        date_str = appointment.date.strftime("%d.%m.%Y")
        time_str = appointment.start_time.strftime("%H:%M")

        send_new_appointment_to_master_task.delay(
            master_email=master.user.email,
            master_name=master.user.full_name or master.user.email,
            client_name=client.full_name or client.email,
            service_name=service_name,
            date=date_str,
            time=time_str,
            price=str(appointment.price)
        )

        # Create in-app notification for master
        NotificationService.notify_new_appointment(
            master_user=master.user,
            client_name=client.full_name or client.email,
            service_name=service_name,
            date=date_str,
            time=time_str
        )

    @extend_schema(
        tags=["Записи"],
        summary="Отменить запись",
        description="Отмена записи клиентом или мастером",
        request=AppointmentCancelSerializer
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel an appointment."""
        appointment = self.get_object()

        if not appointment.can_cancel:
            return Response(
                {"error": "Эту запись нельзя отменить"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = AppointmentCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        appointment.transition_to(Appointment.Status.CANCELLED)
        appointment.cancelled_at = timezone.now()
        appointment.cancellation_reason = serializer.validated_data.get("reason", "")
        appointment.save()

        # Determine who cancelled and who should receive the notification
        user = request.user
        is_master = hasattr(user, "master_profile") and appointment.master == user.master_profile

        if is_master:
            # Master cancelled - notify client
            recipient_email = appointment.client.email
            recipient_name = appointment.client.full_name or appointment.client.email
            cancelled_by = "мастером"
        else:
            # Client cancelled - notify master
            recipient_email = appointment.master.user.email
            recipient_name = appointment.master.user.full_name or appointment.master.user.email
            cancelled_by = "клиентом"

        date_str = appointment.date.strftime("%d.%m.%Y")
        time_str = appointment.start_time.strftime("%H:%M")

        # Get service name (custom service or catalog service)
        if appointment.master_service:
            service_name = appointment.master_service.name
        elif appointment.service:
            service_name = appointment.service.name
        else:
            service_name = "Услуга"

        send_appointment_cancelled_task.delay(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            service_name=service_name,
            date=date_str,
            time=time_str,
            cancelled_by=cancelled_by,
            reason=appointment.cancellation_reason
        )

        # Create in-app notification for the other party
        notify_user = appointment.client if is_master else appointment.master.user
        NotificationService.notify_appointment_cancelled(
            user=notify_user,
            cancelled_by=cancelled_by,
            service_name=service_name,
            date=date_str,
            time=time_str,
            reason=appointment.cancellation_reason
        )

        return Response(AppointmentSerializer(appointment).data)

    @extend_schema(
        tags=["Записи"],
        summary="Подтвердить запись",
        description="Подтверждение записи мастером"
    )
    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        """Confirm an appointment (master only)."""
        appointment = self.get_object()

        if not hasattr(request.user, "master_profile"):
            return Response(
                {"error": "Только мастер может подтвердить запись"},
                status=status.HTTP_403_FORBIDDEN
            )

        if appointment.master != request.user.master_profile:
            return Response(
                {"error": "Вы не можете подтвердить чужую запись"},
                status=status.HTTP_403_FORBIDDEN
            )

        if appointment.is_past:
            return Response(
                {"error": "Нельзя подтвердить запись на прошедшую дату"},
                status=status.HTTP_400_BAD_REQUEST
            )

        appointment.transition_to(Appointment.Status.CONFIRMED)
        appointment.save()

        # Send confirmation email to client
        client = appointment.client
        master = appointment.master
        date_str = appointment.date.strftime("%d.%m.%Y")
        time_str = appointment.start_time.strftime("%H:%M")
        master_name = master.user.full_name or master.user.email

        # Get service name (custom service or catalog service)
        if appointment.master_service:
            service_name = appointment.master_service.name
        elif appointment.service:
            service_name = appointment.service.name
        else:
            service_name = "Услуга"

        send_appointment_confirmation_task.delay(
            client_email=client.email,
            client_name=client.full_name or client.email,
            master_name=master_name,
            service_name=service_name,
            date=date_str,
            time=time_str,
            price=str(appointment.price),
            address=master.address or ""
        )

        # Create in-app notification for client
        NotificationService.notify_appointment_confirmed(
            client_user=client,
            master_name=master_name,
            service_name=service_name,
            date=date_str,
            time=time_str
        )

        return Response(AppointmentSerializer(appointment).data)

    @extend_schema(
        tags=["Записи"],
        summary="Завершить запись",
        description="Отметить запись как выполненную (только мастер)"
    )
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Mark appointment as completed (master only)."""
        appointment = self.get_object()

        if not hasattr(request.user, "master_profile"):
            return Response(
                {"error": "Только мастер может завершить запись"},
                status=status.HTTP_403_FORBIDDEN
            )

        if appointment.master != request.user.master_profile:
            return Response(
                {"error": "Вы не можете завершить чужую запись"},
                status=status.HTTP_403_FORBIDDEN
            )

        appointment.transition_to(Appointment.Status.COMPLETED)
        appointment.save()

        return Response(AppointmentSerializer(appointment).data)

    @extend_schema(
        tags=["Записи"],
        summary="Предстоящие записи",
        description="Получение списка предстоящих записей пользователя"
    )
    @action(detail=False, methods=["get"])
    def upcoming(self, request):
        """Get upcoming appointments for current user."""
        queryset = self.get_queryset().filter(
            date__gte=timezone.now().date(),
            status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED]
        ).order_by("date", "start_time")

        serializer = AppointmentSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=["Записи"],
        summary="Перенести запись",
        description="Перенос записи на другую дату/время",
        request=AppointmentRescheduleSerializer
    )
    @action(detail=True, methods=["post"])
    def reschedule(self, request, pk=None):
        """Reschedule an appointment to a new date/time."""
        appointment = self.get_object()

        # Check if appointment can be rescheduled
        if appointment.status not in [Appointment.Status.PENDING, Appointment.Status.CONFIRMED]:
            return Response(
                {"error": "Можно перенести только ожидающую или подтверждённую запись"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user can reschedule this appointment
        user = request.user
        is_client = appointment.client == user
        is_master = hasattr(user, "master_profile") and appointment.master == user.master_profile

        if not is_client and not is_master and not user.is_staff:
            return Response(
                {"error": "У вас нет прав для переноса этой записи"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check minimum time before appointment (2 hours)
        appointment_datetime = datetime.combine(appointment.date, appointment.start_time)
        if timezone.is_naive(appointment_datetime):
            appointment_datetime = timezone.make_aware(appointment_datetime)

        if appointment_datetime - timezone.now() < timedelta(hours=2):
            return Response(
                {"error": "Перенос возможен не позднее чем за 2 часа до записи"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = AppointmentRescheduleSerializer(
            data=request.data,
            context={"appointment": appointment, "request": request}
        )
        serializer.is_valid(raise_exception=True)

        old_date_str = appointment.date.strftime("%d.%m.%Y")
        old_time_str = appointment.start_time.strftime("%H:%M")

        # Update appointment
        appointment.date = serializer.validated_data["date"]
        appointment.start_time = serializer.validated_data["start_time"]
        appointment.end_time = serializer.validated_data["end_time"]
        # Reset status to pending after reschedule
        appointment.status = Appointment.Status.PENDING
        appointment.save()

        new_date_str = appointment.date.strftime("%d.%m.%Y")
        new_time_str = appointment.start_time.strftime("%H:%M")

        # Get service name (custom service or catalog service)
        if appointment.master_service:
            service_name = appointment.master_service.name
        elif appointment.service:
            service_name = appointment.service.name
        else:
            service_name = "Услуга"

        # Determine who rescheduled and send notifications
        if is_master:
            # Master rescheduled - notify client
            NotificationService.notify_appointment_rescheduled(
                user=appointment.client,
                rescheduled_by="мастером",
                service_name=service_name,
                old_date=old_date_str,
                old_time=old_time_str,
                new_date=new_date_str,
                new_time=new_time_str
            )
        else:
            # Client rescheduled - notify master
            NotificationService.notify_appointment_rescheduled(
                user=appointment.master.user,
                rescheduled_by="клиентом",
                service_name=service_name,
                old_date=old_date_str,
                old_time=old_time_str,
                new_date=new_date_str,
                new_time=new_time_str
            )

        return Response(AppointmentSerializer(appointment).data)


@extend_schema(
    tags=["Записи"],
    summary="Доступные слоты",
    description="Получение доступных временных слотов для записи к мастеру"
)
class AvailableSlotsView(generics.GenericAPIView):
    """Get available time slots for booking."""

    permission_classes = [AllowAny]
    serializer_class = AvailableSlotsSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        master_id = serializer.validated_data["master_id"]
        service_id = serializer.validated_data["service_id"]
        date = serializer.validated_data["date"]

        try:
            master = MasterProfile.objects.get(id=master_id)
            # Try to find MasterService by its ID first (for custom services)
            # then fallback to finding by catalog service_id
            try:
                master_service = MasterService.objects.get(id=service_id, master=master)
            except MasterService.DoesNotExist:
                master_service = MasterService.objects.get(master=master, service_id=service_id)
        except (MasterProfile.DoesNotExist, MasterService.DoesNotExist):
            return Response({"slots": []})

        schedule = WorkSchedule.objects.filter(
            master=master,
            weekday=date.weekday(),
            is_working=True
        ).first()

        if not schedule:
            return Response({"slots": []})

        duration = master_service.actual_duration
        slot_duration = timedelta(minutes=duration)

        existing_appointments = Appointment.objects.filter(
            master=master,
            date=date,
            status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED],
            is_archived=False
        )

        slots = []
        current_time = timezone.make_aware(datetime.combine(date, schedule.start_time))
        end_datetime = timezone.make_aware(datetime.combine(date, schedule.end_time))
        now = timezone.now()
        is_today = date == now.date()

        while current_time + slot_duration <= end_datetime:
            slot_end = current_time + slot_duration
            is_available = True

            # Skip past time slots for today
            if is_today and current_time <= now:
                current_time += timedelta(minutes=30)
                continue

            for appt in existing_appointments:
                appt_start = timezone.make_aware(datetime.combine(date, appt.start_time))
                appt_end = timezone.make_aware(datetime.combine(date, appt.end_time))

                if not (slot_end <= appt_start or current_time >= appt_end):
                    is_available = False
                    break

            if is_available:
                slots.append({
                    "start_time": current_time.time().strftime("%H:%M"),
                    "end_time": slot_end.time().strftime("%H:%M"),
                })

            current_time += timedelta(minutes=30)

        return Response({"slots": slots})


@extend_schema_view(
    list=extend_schema(tags=["Отзывы"], summary="Список отзывов"),
    retrieve=extend_schema(tags=["Отзывы"], summary="Детали отзыва"),
    create=extend_schema(tags=["Отзывы"], summary="Создать отзыв"),
    update=extend_schema(tags=["Отзывы"], summary="Обновить отзыв"),
    partial_update=extend_schema(tags=["Отзывы"], summary="Частичное обновление отзыва"),
    destroy=extend_schema(tags=["Отзывы"], summary="Удалить отзыв"),
)
class ReviewViewSet(viewsets.ModelViewSet):
    """ViewSet for reviews."""

    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = Review.objects.select_related(
            "appointment__client",
            "appointment__master__user"
        )
        # Filter to only client's own reviews when ?my=true
        if self.request.query_params.get("my") == "true" and self.request.user.is_authenticated:
            qs = qs.filter(appointment__client=self.request.user)
        return qs

    def get_permissions(self):
        if self.action in ["list", "by_master"]:
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        """Create review and send email notification to master."""
        review = serializer.save()

        # Send notification to master
        appointment = review.appointment
        master = appointment.master
        client = appointment.client
        client_name = client.full_name or client.email

        send_review_notification_task.delay(
            master_email=master.user.email,
            master_name=master.user.full_name or master.user.email,
            client_name=client_name,
            rating=review.rating,
            comment=review.comment or ""
        )

        # Create in-app notification for master
        NotificationService.notify_new_review(
            master_user=master.user,
            client_name=client_name,
            rating=review.rating,
            comment=review.comment or ""
        )

    @extend_schema(
        tags=["Отзывы"],
        summary="Отзывы мастера",
        description="Получение всех отзывов для конкретного мастера"
    )
    @action(detail=False, methods=["get"], url_path="master/(?P<master_id>[^/.]+)")
    def by_master(self, request, master_id=None):
        """Get reviews for a specific master."""
        reviews = self.get_queryset().filter(appointment__master_id=master_id)
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)
