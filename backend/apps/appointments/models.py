"""
Models for appointment booking.
"""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel
from apps.services.models import MasterService, Service
from apps.users.models import MasterProfile, User


class WorkSchedule(BaseModel):
    """Master work schedule."""

    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Понедельник"
        TUESDAY = 1, "Вторник"
        WEDNESDAY = 2, "Среда"
        THURSDAY = 3, "Четверг"
        FRIDAY = 4, "Пятница"
        SATURDAY = 5, "Суббота"
        SUNDAY = 6, "Воскресенье"

    master = models.ForeignKey(
        MasterProfile,
        on_delete=models.CASCADE,
        related_name="schedules"
    )
    weekday = models.IntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_working = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Расписание"
        verbose_name_plural = "Расписания"
        unique_together = ["master", "weekday"]
        ordering = ["weekday", "start_time"]

    def __str__(self):
        return f"{self.master.user.full_name} - {self.get_weekday_display()}"


class Appointment(BaseModel):
    """Appointment booking model."""

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает подтверждения"
        CONFIRMED = "confirmed", "Подтверждено"
        CANCELLED = "cancelled", "Отменено"
        COMPLETED = "completed", "Завершено"
        NO_SHOW = "no_show", "Клиент не пришёл"

    client = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="client_appointments"
    )
    master = models.ForeignKey(
        MasterProfile,
        on_delete=models.CASCADE,
        related_name="master_appointments"
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="appointments",
        null=True,
        blank=True
    )
    master_service = models.ForeignKey(
        MasterService,
        on_delete=models.SET_NULL,
        related_name="appointments",
        null=True,
        blank=True
    )
    date = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    is_archived = models.BooleanField(default=False, db_index=True)

    VALID_TRANSITIONS = {
        "pending": ["confirmed", "cancelled"],
        "confirmed": ["completed", "cancelled", "no_show"],
        "completed": [],
        "cancelled": [],
        "no_show": [],
    }

    class Meta:
        verbose_name = "Запись"
        verbose_name_plural = "Записи"
        ordering = ["-date", "-start_time"]
        indexes = [
            models.Index(fields=["master", "date", "status"]),
        ]

    def __str__(self):
        return f"{self.client.full_name} -> {self.master.user.full_name} ({self.date})"

    def transition_to(self, new_status):
        allowed = self.VALID_TRANSITIONS.get(self.status, [])
        if new_status not in allowed:
            raise ValidationError(
                f"Нельзя перевести из '{self.get_status_display()}' в '{new_status}'"
            )
        self.status = new_status

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError("Время начала должно быть раньше времени окончания")
        if self.date < timezone.now().date():
            raise ValidationError("Нельзя создать запись на прошедшую дату")

    @property
    def is_past(self):
        now = timezone.now()
        appointment_datetime = timezone.make_aware(
            timezone.datetime.combine(self.date, self.end_time)
        )
        return appointment_datetime < now

    @property
    def can_cancel(self):
        if self.status in [self.Status.CANCELLED, self.Status.COMPLETED, self.Status.NO_SHOW]:
            return False
        now = timezone.now()
        appointment_datetime = timezone.make_aware(
            timezone.datetime.combine(self.date, self.start_time)
        )
        return appointment_datetime - now >= timedelta(hours=2)


class Review(BaseModel):
    """Review for completed appointment."""

    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name="review"
    )
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Отзыв от {self.appointment.client.full_name}"

    def clean(self):
        if not 1 <= self.rating <= 5:
            raise ValidationError("Рейтинг должен быть от 1 до 5")
        if self.appointment.status != Appointment.Status.COMPLETED:
            raise ValidationError("Отзыв можно оставить только для завершённой записи")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._update_master_rating()

    def _update_master_rating(self):
        master = self.appointment.master
        result = Review.objects.filter(appointment__master=master).aggregate(
            avg=models.Avg("rating"), count=models.Count("id")
        )
        master.rating = round(result["avg"] or 0, 2)
        master.reviews_count = result["count"]
        master.save(update_fields=["rating", "reviews_count"])
