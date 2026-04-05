"""
Notification service for creating in-app notifications.
"""

import logging

from .models import Notification

logger = logging.getLogger(__name__)

# Notification types that require advanced_notifications in subscription plan
ADVANCED_NOTIFICATION_TYPES = {
    Notification.NotificationType.APPOINTMENT_REMINDER,
    Notification.NotificationType.REVIEW_NEW,
}


class NotificationService:
    """Service class for creating notifications."""

    @staticmethod
    def create_notification(
        user,
        notification_type: str,
        title: str,
        message: str,
        link: str = ""
    ) -> Notification | None:
        """Create a new notification for a user.

        Advanced notification types are only created for users
        with advanced_notifications enabled in their subscription plan.
        """
        if notification_type in ADVANCED_NOTIFICATION_TYPES:
            sub = getattr(user, "subscription", None)
            if not sub or not sub.plan.advanced_notifications:
                logger.debug(
                    "Skipping advanced notification %s for user %s (no PRO)",
                    notification_type, user.id,
                )
                return None

        return Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link
        )

    @classmethod
    def notify_new_appointment(cls, master_user, client_name: str, service_name: str, date: str, time: str):
        """Notify master about new appointment."""
        return cls.create_notification(
            user=master_user,
            notification_type=Notification.NotificationType.APPOINTMENT_NEW,
            title="Новая запись",
            message=f"Клиент {client_name} записался на услугу «{service_name}» на {date} в {time}",
            link="/master/appointments"
        )

    @classmethod
    def notify_appointment_confirmed(cls, client_user, master_name: str, service_name: str, date: str, time: str):
        """Notify client about confirmed appointment."""
        return cls.create_notification(
            user=client_user,
            notification_type=Notification.NotificationType.APPOINTMENT_CONFIRMED,
            title="Запись подтверждена",
            message=f"Мастер {master_name} подтвердил вашу запись на «{service_name}» на {date} в {time}",
            link="/client/my-appointments"
        )

    @classmethod
    def notify_appointment_cancelled(cls, user, cancelled_by: str, service_name: str, date: str, time: str, reason: str = ""):
        """Notify user about cancelled appointment."""
        message = f"Запись на «{service_name}» на {date} в {time} отменена {cancelled_by}"
        if reason:
            message += f". Причина: {reason}"

        link = "/master/appointments" if cancelled_by == "клиентом" else "/client/my-appointments"

        return cls.create_notification(
            user=user,
            notification_type=Notification.NotificationType.APPOINTMENT_CANCELLED,
            title="Запись отменена",
            message=message,
            link=link
        )

    @classmethod
    def notify_appointment_rescheduled(
        cls,
        user,
        rescheduled_by: str,
        service_name: str,
        old_date: str,
        old_time: str,
        new_date: str,
        new_time: str
    ):
        """Notify user about rescheduled appointment."""
        message = f"Запись на «{service_name}» перенесена {rescheduled_by} с {old_date} {old_time} на {new_date} {new_time}"
        link = "/master/appointments" if rescheduled_by == "клиентом" else "/client/my-appointments"

        return cls.create_notification(
            user=user,
            notification_type=Notification.NotificationType.APPOINTMENT_RESCHEDULED,
            title="Запись перенесена",
            message=message,
            link=link
        )

    @classmethod
    def notify_appointment_reminder(cls, user, service_name: str, master_name: str, date: str, time: str, hours_before: int = 24):
        """Notify user about upcoming appointment."""
        return cls.create_notification(
            user=user,
            notification_type=Notification.NotificationType.APPOINTMENT_REMINDER,
            title="Напоминание о записи",
            message=f"Напоминаем: через {hours_before} часов у вас запись на «{service_name}» к мастеру {master_name}",
            link="/client/my-appointments"
        )

    @classmethod
    def notify_new_review(cls, master_user, client_name: str, rating: int, comment: str = ""):
        """Notify master about new review."""
        stars = "★" * rating + "☆" * (5 - rating)
        message = f"Клиент {client_name} оставил отзыв: {stars}"
        if comment:
            message += f' "{comment[:50]}..."' if len(comment) > 50 else f' "{comment}"'

        return cls.create_notification(
            user=master_user,
            notification_type=Notification.NotificationType.REVIEW_NEW,
            title="Новый отзыв",
            message=message,
            link="/master/dashboard"
        )

    @classmethod
    def notify_chat_message(cls, recipient_user, sender_name: str, message_preview: str, chat_id: str):
        """Notify user about new chat message."""
        preview = message_preview[:100] + "..." if len(message_preview) > 100 else message_preview
        # Determine link based on user role
        if recipient_user.role == 'master':
            link = f"/master/chat?id={chat_id}"
        else:
            link = f"/client/chat?id={chat_id}"

        return cls.create_notification(
            user=recipient_user,
            notification_type=Notification.NotificationType.CHAT_MESSAGE,
            title=f"Сообщение от {sender_name}",
            message=preview,
            link=link
        )

    @classmethod
    def notify_system(cls, user, title: str, message: str, link: str = ""):
        """Create system notification."""
        return cls.create_notification(
            user=user,
            notification_type=Notification.NotificationType.SYSTEM,
            title=title,
            message=message,
            link=link
        )
