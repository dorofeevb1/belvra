from datetime import timedelta

from celery import shared_task
from django.utils import timezone


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
            # Get service name (custom service or catalog service)
            if appointment.master_service:
                service_name = appointment.master_service.name
            elif appointment.service:
                service_name = appointment.service.name
            else:
                service_name = "Услуга"

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
            print(f"Error sending reminder for appointment {appointment.id}: {e}")

    return f"Sent {sent_count} reminders"


@shared_task
def cleanup_old_appointments():
    """Archive old completed appointments."""
    from .models import Appointment

    cutoff_date = timezone.now().date() - timedelta(days=365)
    old_appointments = Appointment.objects.filter(
        date__lt=cutoff_date,
        status__in=[Appointment.Status.COMPLETED, Appointment.Status.CANCELLED]
    )
    count = old_appointments.count()
    # Instead of deleting, you might want to archive
    # old_appointments.delete()
    return f"Found {count} old appointments for archiving"


@shared_task
def mark_no_show_appointments():
    """Mark appointments as no-show if not completed after end time."""
    from .models import Appointment

    now = timezone.now()
    yesterday = now.date() - timedelta(days=1)

    appointments = Appointment.objects.filter(
        date=yesterday,
        status=Appointment.Status.CONFIRMED
    )

    count = appointments.update(status=Appointment.Status.NO_SHOW)
    return f"Marked {count} appointments as no-show"
