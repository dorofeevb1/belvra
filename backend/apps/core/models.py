"""
Abstract base models for the project.
"""

import uuid

from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    """Abstract model with created and updated timestamps."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """Abstract model with UUID primary key."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class BaseModel(UUIDModel, TimeStampedModel):
    """Abstract base model combining UUID and timestamps."""

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class Notification(BaseModel):
    """In-app notification model."""

    class NotificationType(models.TextChoices):
        APPOINTMENT_NEW = "appointment_new", "Новая запись"
        APPOINTMENT_CONFIRMED = "appointment_confirmed", "Запись подтверждена"
        APPOINTMENT_CANCELLED = "appointment_cancelled", "Запись отменена"
        APPOINTMENT_RESCHEDULED = "appointment_rescheduled", "Запись перенесена"
        APPOINTMENT_REMINDER = "appointment_reminder", "Напоминание о записи"
        APPOINTMENT_COMPLETED = "appointment_completed", "Запись завершена"
        REVIEW_NEW = "review_new", "Новый отзыв"
        PAYMENT_RECEIVED = "payment_received", "Платёж получен"
        PAYMENT_REFUNDED = "payment_refunded", "Возврат платежа"
        SYSTEM = "system", "Системное"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.user.email}"

    def mark_as_read(self):
        """Mark notification as read."""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at", "updated_at"])
