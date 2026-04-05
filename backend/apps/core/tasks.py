"""
Celery tasks for core functionality like email sending.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .email import EmailService

logger = logging.getLogger(__name__)


@shared_task
def cleanup_unverified_accounts():
    """Delete accounts that were not verified within 5 minutes."""
    from apps.users.models import User

    cutoff = timezone.now() - timedelta(minutes=5)
    unverified = User.objects.filter(
        is_verified=False,
        is_staff=False,
        created_at__lt=cutoff,
    )
    count = unverified.count()
    if count:
        unverified.delete()
        logger.info(f"Deleted {count} unverified accounts older than 5 minutes")
    return count


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_welcome_email_task(self, user_id: str):
    """Send welcome email to newly registered user."""
    from apps.users.models import User

    try:
        user = User.objects.get(id=user_id)
        EmailService.send_welcome_email(user)
        logger.info(f"Welcome email sent to {user.email}")
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for welcome email")
    except Exception as exc:
        logger.error(f"Failed to send welcome email: {exc}")
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_verification_code_task(self, user_id: str, code: str):
    """Send email verification code."""
    from apps.users.models import User

    try:
        user = User.objects.get(id=user_id)
        EmailService.send_email_verification_code(user, code)
        logger.info(f"Verification code sent to {user.email}")
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for verification email")
    except Exception as exc:
        logger.error(f"Failed to send verification email: {exc}")
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_password_reset_email_task(self, user_id: str, reset_url: str):
    """Send password reset email."""
    from apps.users.models import User

    try:
        user = User.objects.get(id=user_id)
        EmailService.send_password_reset(user, reset_url)
        logger.info(f"Password reset email sent to {user.email}")
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for password reset email")
    except Exception as exc:
        logger.error(f"Failed to send password reset email: {exc}")
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_appointment_confirmation_task(
    self,
    client_email: str,
    client_name: str,
    master_name: str,
    service_name: str,
    date: str,
    time: str,
    price: str,
    address: str = ""
):
    """Send appointment confirmation to client."""
    try:
        EmailService.send_appointment_confirmation(
            client_email=client_email,
            client_name=client_name,
            master_name=master_name,
            service_name=service_name,
            date=date,
            time=time,
            price=price,
            address=address
        )
        logger.info(f"Appointment confirmation sent to {client_email}")
    except Exception as exc:
        logger.error(f"Failed to send appointment confirmation: {exc}")
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_appointment_reminder_task(
    self,
    client_email: str,
    client_name: str,
    master_name: str,
    service_name: str,
    date: str,
    time: str,
    hours_before: int = 24
):
    """Send appointment reminder to client."""
    try:
        EmailService.send_appointment_reminder(
            client_email=client_email,
            client_name=client_name,
            master_name=master_name,
            service_name=service_name,
            date=date,
            time=time,
            hours_before=hours_before
        )
        logger.info(f"Appointment reminder sent to {client_email}")
    except Exception as exc:
        logger.error(f"Failed to send appointment reminder: {exc}")
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_appointment_cancelled_task(
    self,
    recipient_email: str,
    recipient_name: str,
    service_name: str,
    date: str,
    time: str,
    cancelled_by: str,
    reason: str = ""
):
    """Send appointment cancellation notification."""
    try:
        EmailService.send_appointment_cancelled(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            service_name=service_name,
            date=date,
            time=time,
            cancelled_by=cancelled_by,
            reason=reason
        )
        logger.info(f"Cancellation email sent to {recipient_email}")
    except Exception as exc:
        logger.error(f"Failed to send cancellation email: {exc}")
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_new_appointment_to_master_task(
    self,
    master_email: str,
    master_name: str,
    client_name: str,
    service_name: str,
    date: str,
    time: str,
    price: str
):
    """Send new appointment notification to master."""
    try:
        EmailService.send_new_appointment_to_master(
            master_email=master_email,
            master_name=master_name,
            client_name=client_name,
            service_name=service_name,
            date=date,
            time=time,
            price=price
        )
        logger.info(f"New appointment notification sent to master {master_email}")
    except Exception as exc:
        logger.error(f"Failed to send new appointment notification: {exc}")
        self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_review_notification_task(
    self,
    master_email: str,
    master_name: str,
    client_name: str,
    rating: int,
    comment: str = ""
):
    """Send new review notification to master."""
    try:
        EmailService.send_review_notification(
            master_email=master_email,
            master_name=master_name,
            client_name=client_name,
            rating=rating,
            comment=comment
        )
        logger.info(f"Review notification sent to master {master_email}")
    except Exception as exc:
        logger.error(f"Failed to send review notification: {exc}")
        self.retry(exc=exc)


@shared_task
def send_rebooking_reminders():
    """Remind clients to rebook with masters who have rebooking reminders enabled (PRO)."""
    from apps.appointments.models import Appointment
    from apps.users.models import MasterProfile
    from .notifications import NotificationService

    masters = MasterProfile.objects.filter(
        rebooking_reminder_days__gt=0,
        user__subscription__status="active",
        user__subscription__plan__rebooking_reminder_enabled=True,
    ).select_related("user__subscription__plan")

    now = timezone.now().date()
    sent = 0

    for master in masters:
        days = master.rebooking_reminder_days
        target_date = now - timedelta(days=days)

        appointments = Appointment.objects.filter(
            master=master,
            status=Appointment.Status.COMPLETED,
            date=target_date,
        ).select_related("client", "master_service", "service")

        for appt in appointments:
            has_upcoming = Appointment.objects.filter(
                client=appt.client,
                master=master,
                date__gte=now,
                status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED],
            ).exists()

            if has_upcoming:
                continue

            service_name = (
                appt.master_service.name if appt.master_service
                else (appt.service.name if appt.service else "услугу")
            )
            master_name = master.user.full_name or master.user.email

            NotificationService.create_notification(
                user=appt.client,
                notification_type="system",
                title="Пора записаться снова",
                message=(
                    f"Прошло {days} дней с вашего визита на «{service_name}» "
                    f"к мастеру {master_name}. Запишитесь снова!"
                ),
                link=f"/client/master/{master.id}",
            )
            sent += 1

    logger.info(f"Sent {sent} rebooking reminders")
    return sent
