from datetime import datetime, timedelta

from django.utils import timezone
from rest_framework import serializers

from apps.services.serializers import ServiceSerializer
from apps.users.serializers import MasterProfileSerializer, UserSerializer

from .models import Appointment, Review, WorkSchedule


class WorkScheduleSerializer(serializers.ModelSerializer):
    """Serializer for WorkSchedule."""

    weekday_display = serializers.CharField(source="get_weekday_display", read_only=True)

    class Meta:
        model = WorkSchedule
        fields = ["id", "weekday", "weekday_display", "start_time", "end_time", "is_working"]


class AppointmentSerializer(serializers.ModelSerializer):
    """Serializer for Appointment."""

    client = UserSerializer(read_only=True)
    master = MasterProfileSerializer(read_only=True)
    service = ServiceSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    can_cancel = serializers.BooleanField(read_only=True)
    service_name = serializers.SerializerMethodField()
    prepaid = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            "id", "client", "master", "service", "service_name", "date", "start_time",
            "end_time", "status", "status_display", "price", "notes",
            "can_cancel", "created_at", "prepaid", "payment_status"
        ]

    def get_service_name(self, obj):
        """Get service name from master_service or service."""
        if obj.master_service:
            return obj.master_service.name
        if obj.service:
            return obj.service.name
        return None

    def get_prepaid(self, obj):
        """Get total amount paid for this appointment."""
        from django.db.models import Sum
        total = obj.payments.filter(status="succeeded").aggregate(Sum("amount"))["amount__sum"]
        return float(total) if total else 0

    def get_payment_status(self, obj):
        """Get payment status: paid, partial, or unpaid."""
        prepaid = self.get_prepaid(obj)
        if prepaid >= float(obj.price):
            return "paid"
        elif prepaid > 0:
            return "partial"
        return "unpaid"


class AppointmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating appointments."""

    master_id = serializers.UUIDField(write_only=True)
    service_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Appointment
        fields = ["master_id", "service_id", "date", "start_time", "notes"]

    def validate_date(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError("Нельзя записаться на прошедшую дату")
        if value > timezone.now().date() + timedelta(days=30):
            raise serializers.ValidationError("Запись возможна не более чем за 30 дней")
        return value

    def validate(self, attrs):
        from apps.users.models import MasterProfile
        from apps.services.models import Service, MasterService

        try:
            master = MasterProfile.objects.get(id=attrs["master_id"])
        except MasterProfile.DoesNotExist:
            raise serializers.ValidationError({"master_id": "Мастер не найден"})

        service_id = attrs["service_id"]
        master_service = None
        service = None

        # Try to find MasterService by ID first (for custom services)
        try:
            master_service = MasterService.objects.get(id=service_id, master=master)
            service = master_service.service  # May be None for custom services
        except MasterService.DoesNotExist:
            # Fallback: try to find by catalog Service ID
            try:
                service = Service.objects.get(id=service_id)
                master_service = MasterService.objects.get(master=master, service=service)
            except (Service.DoesNotExist, MasterService.DoesNotExist):
                raise serializers.ValidationError({"service_id": "Услуга не найдена"})

        schedule = WorkSchedule.objects.filter(
            master=master,
            weekday=attrs["date"].weekday(),
            is_working=True
        ).first()

        if not schedule:
            raise serializers.ValidationError("Мастер не работает в этот день")

        start_time = attrs["start_time"]
        if start_time < schedule.start_time or start_time >= schedule.end_time:
            raise serializers.ValidationError("Выбранное время вне рабочих часов")
        duration = master_service.actual_duration
        end_time = (datetime.combine(attrs["date"], start_time) + timedelta(minutes=duration)).time()

        existing = Appointment.objects.filter(
            master=master,
            date=attrs["date"],
            status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED]
        ).exclude(
            end_time__lte=start_time
        ).exclude(
            start_time__gte=end_time
        )

        if existing.exists():
            raise serializers.ValidationError("Это время уже занято")

        attrs["master"] = master
        attrs["service"] = service  # May be None for custom services
        attrs["master_service"] = master_service
        attrs["end_time"] = end_time
        attrs["price"] = master_service.actual_price

        return attrs

    def create(self, validated_data):
        validated_data.pop("master_id")
        validated_data.pop("service_id")
        validated_data["client"] = self.context["request"].user
        return super().create(validated_data)


class AppointmentCancelSerializer(serializers.Serializer):
    """Serializer for cancelling appointments."""

    reason = serializers.CharField(required=False, allow_blank=True)


class AppointmentRescheduleSerializer(serializers.Serializer):
    """Serializer for rescheduling appointments."""

    date = serializers.DateField()
    start_time = serializers.TimeField()

    def validate_date(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError("Нельзя перенести на прошедшую дату")
        if value > timezone.now().date() + timedelta(days=30):
            raise serializers.ValidationError("Перенос возможен не более чем за 30 дней")
        return value

    def validate(self, attrs):
        appointment = self.context.get("appointment")
        if not appointment:
            return attrs

        master = appointment.master
        new_date = attrs["date"]
        new_start_time = attrs["start_time"]

        # Check if master works on the new date
        schedule = WorkSchedule.objects.filter(
            master=master,
            weekday=new_date.weekday(),
            is_working=True
        ).first()

        if not schedule:
            raise serializers.ValidationError({"date": "Мастер не работает в этот день"})

        # Check if time is within working hours
        if new_start_time < schedule.start_time or new_start_time >= schedule.end_time:
            raise serializers.ValidationError({"start_time": "Выбранное время вне рабочих часов"})

        # Calculate new end time
        duration = (datetime.combine(new_date, appointment.end_time) -
                    datetime.combine(new_date, appointment.start_time)).total_seconds() / 60
        new_end_time = (datetime.combine(new_date, new_start_time) + timedelta(minutes=duration)).time()

        # Check for conflicts with existing appointments (excluding current one)
        existing = Appointment.objects.filter(
            master=master,
            date=new_date,
            status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED]
        ).exclude(
            id=appointment.id
        ).exclude(
            end_time__lte=new_start_time
        ).exclude(
            start_time__gte=new_end_time
        )

        if existing.exists():
            raise serializers.ValidationError("Это время уже занято")

        attrs["end_time"] = new_end_time
        return attrs


class ReviewSerializer(serializers.ModelSerializer):
    """Serializer for Review."""

    client_name = serializers.CharField(source="appointment.client.full_name", read_only=True)

    class Meta:
        model = Review
        fields = ["id", "appointment", "rating", "comment", "client_name", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Рейтинг должен быть от 1 до 5")
        return value

    def validate_appointment(self, value):
        if value.status != Appointment.Status.COMPLETED:
            raise serializers.ValidationError("Можно оставить отзыв только для завершённой записи")
        if value.client != self.context["request"].user:
            raise serializers.ValidationError("Вы можете оставить отзыв только для своей записи")
        if hasattr(value, "review"):
            raise serializers.ValidationError("Отзыв для этой записи уже существует")
        return value


class AvailableSlotsSerializer(serializers.Serializer):
    """Serializer for available time slots request."""

    master_id = serializers.UUIDField()
    service_id = serializers.UUIDField()
    date = serializers.DateField()
