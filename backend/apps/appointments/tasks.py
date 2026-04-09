from datetime import timedelta

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def send_appointment_reminders():
    """Send reminders for upcoming appointments."""
    from apps.core.tasks import send_appointment_reminder_task
    from apps.core.notifications import NotificationService

    from .models import Appointment

    tomorrow = timezone.now().date() + timedelta(days=1)
    appointments = Appointment.objects.filter(
        date=tomorrow,
        status=Appointment.Status.CONFIRMED
    ).select_related("client", "master__user", "service")

    sent_count = 0
    for appointment in appointments:
        try:
            service_name = appointment.service_name

            if not appointment.client:
                continue

            # Send email reminder
            send_appointment_reminder_task.delay(
                client_email=appointment.client.email,
                client_name=appointment.client.full_name,
                master_name=appointment.master.user.full_name,
                service_name=service_name,
                date=appointment.date.strftime("%d.%m.%Y"),
                time=appointment.start_time.strftime("%H:%M"),
                hours_before=24
            )

            # Create in-app notification
            NotificationService.notify_appointment_reminder(
                user=appointment.client,
                service_name=service_name,
                master_name=appointment.master.user.full_name,
                date=appointment.date.strftime("%d.%m.%Y"),
                time=appointment.start_time.strftime("%H:%M"),
                hours_before=24
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Error sending reminder for appointment {appointment.id}: {e}")

    return f"Sent {sent_count} reminders"


@shared_task
def cleanup_old_appointments():
    """Archive old completed appointments (soft delete)."""
    from .models import Appointment

    cutoff_date = timezone.now().date() - timedelta(days=365)
    old_appointments = Appointment.objects.filter(
        date__lt=cutoff_date,
        status__in=[
            Appointment.Status.COMPLETED,
            Appointment.Status.CANCELLED,
            Appointment.Status.NO_SHOW
        ],
        is_archived=False
    )
    count = old_appointments.update(is_archived=True)
    return f"Archived {count} old appointments"


@shared_task
def mark_no_show_appointments():
    """Auto-complete past confirmed appointments or mark as no-show."""
    from .models import Appointment

    now = timezone.now()
    today = now.date()
    current_time = now.time()

    # Подтверждённые записи на прошлые даты — автозавершение
    # (мастер подтвердил = клиент скорее всего пришёл)
    completed_count = Appointment.objects.filter(
        date__lt=today,
        status=Appointment.Status.CONFIRMED,
        is_archived=False
    ).update(status=Appointment.Status.COMPLETED)

    # Сегодняшние записи с истёкшим временем — автозавершение
    today_completed = Appointment.objects.filter(
        date=today,
        end_time__lt=current_time,
        status=Appointment.Status.CONFIRMED,
        is_archived=False
    ).update(status=Appointment.Status.COMPLETED)

    # PENDING записи на прошлые даты — не явился (не подтверждено)
    no_show_count = Appointment.objects.filter(
        date__lt=today,
        status=Appointment.Status.PENDING,
        is_archived=False
    ).update(status=Appointment.Status.NO_SHOW)

    total = completed_count + today_completed + no_show_count
    return (
        f"Auto-completed: {completed_count + today_completed}, "
        f"No-show: {no_show_count}, Total: {total}"
    )


@shared_task
def send_completion_reminder():
    """Send reminder to master to mark appointment as completed 1 hour after end time."""
    from apps.core.notifications import NotificationService

    from .models import Appointment

    now = timezone.now()
    today = now.date()

    # Calculate the time window: appointments that ended 1 hour ago (within 5 min window)
    one_hour_ago = (now - timedelta(hours=1)).time()
    window_start = (now - timedelta(hours=1, minutes=5)).time()

    # Find CONFIRMED appointments that ended about 1 hour ago
    appointments = Appointment.objects.filter(
        date=today,
        end_time__gte=window_start,
        end_time__lt=one_hour_ago,
        status=Appointment.Status.CONFIRMED,
        is_archived=False
    ).select_related("master__user", "client", "service", "master_service")

    sent_count = 0
    for appointment in appointments:
        try:
            service_name = appointment.service_name

            client_name = (appointment.client.full_name or appointment.client.email) if appointment.client else appointment.display_client_name

            # Create in-app notification for master
            NotificationService.create_notification(
                user=appointment.master.user,
                notification_type="completion_reminder",
                title="Не забудьте отметить запись",
                message=f"Пожалуйста, отметьте запись с {client_name} ({service_name}) как завершённую",
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Error sending completion reminder for appointment {appointment.id}: {e}")

    return f"Sent {sent_count} completion reminders"
