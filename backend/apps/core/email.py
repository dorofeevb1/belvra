"""
Email service for sending various notifications.
"""

import logging
from typing import List, Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails."""

    @staticmethod
    def send_email(
        subject: str,
        template_name: str,
        context: dict,
        to_emails: List[str],
        from_email: Optional[str] = None
    ) -> bool:
        """
        Send an email using a template.

        Args:
            subject: Email subject
            template_name: Name of the template (without extension)
            context: Context variables for the template
            to_emails: List of recipient email addresses
            from_email: Sender email (optional, uses DEFAULT_FROM_EMAIL)

        Returns:
            True if email was sent successfully, False otherwise
        """
        try:
            # Add common context
            context['frontend_url'] = settings.FRONTEND_URL
            context['support_email'] = 'support@beautybook.ru'

            # Render HTML content
            html_content = render_to_string(f'emails/{template_name}.html', context)
            text_content = strip_tags(html_content)

            # Create email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email or settings.DEFAULT_FROM_EMAIL,
                to=to_emails
            )
            email.attach_alternative(html_content, "text/html")

            # Send email
            email.send(fail_silently=False)
            logger.info(f"Email sent successfully to {to_emails}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_emails}: {str(e)}")
            return False

    @classmethod
    def send_welcome_email(cls, user) -> bool:
        """Send welcome email after registration."""
        return cls.send_email(
            subject="Добро пожаловать в BeautyBook!",
            template_name="welcome",
            context={
                'user': user,
                'name': user.first_name or user.email.split('@')[0],
            },
            to_emails=[user.email]
        )

    @classmethod
    def send_email_verification_code(cls, user, code: str) -> bool:
        """Send email verification code."""
        return cls.send_email(
            subject="Код подтверждения - BeautyBook",
            template_name="email_verification_code",
            context={
                'user': user,
                'name': user.first_name or user.email.split('@')[0],
                'code': code,
            },
            to_emails=[user.email]
        )

    @classmethod
    def send_password_reset(cls, user, reset_url: str) -> bool:
        """Send password reset link."""
        return cls.send_email(
            subject="Сброс пароля - BeautyBook",
            template_name="password_reset",
            context={
                'user': user,
                'name': user.first_name or user.email.split('@')[0],
                'reset_url': reset_url,
            },
            to_emails=[user.email]
        )

    @classmethod
    def send_appointment_confirmation(
        cls,
        client_email: str,
        client_name: str,
        master_name: str,
        service_name: str,
        date: str,
        time: str,
        price: str,
        address: str = ""
    ) -> bool:
        """Send appointment confirmation to client."""
        return cls.send_email(
            subject=f"Запись подтверждена - {service_name}",
            template_name="appointment_confirmation",
            context={
                'client_name': client_name,
                'master_name': master_name,
                'service_name': service_name,
                'date': date,
                'time': time,
                'price': price,
                'address': address,
            },
            to_emails=[client_email]
        )

    @classmethod
    def send_appointment_reminder(
        cls,
        client_email: str,
        client_name: str,
        master_name: str,
        service_name: str,
        date: str,
        time: str,
        hours_before: int = 24
    ) -> bool:
        """Send appointment reminder to client."""
        return cls.send_email(
            subject=f"Напоминание о записи - {service_name}",
            template_name="appointment_reminder",
            context={
                'client_name': client_name,
                'master_name': master_name,
                'service_name': service_name,
                'date': date,
                'time': time,
                'hours_before': hours_before,
            },
            to_emails=[client_email]
        )

    @classmethod
    def send_appointment_cancelled(
        cls,
        recipient_email: str,
        recipient_name: str,
        service_name: str,
        date: str,
        time: str,
        cancelled_by: str,
        reason: str = ""
    ) -> bool:
        """Send appointment cancellation notification."""
        return cls.send_email(
            subject=f"Запись отменена - {service_name}",
            template_name="appointment_cancelled",
            context={
                'recipient_name': recipient_name,
                'service_name': service_name,
                'date': date,
                'time': time,
                'cancelled_by': cancelled_by,
                'reason': reason,
            },
            to_emails=[recipient_email]
        )

    @classmethod
    def send_new_appointment_to_master(
        cls,
        master_email: str,
        master_name: str,
        client_name: str,
        service_name: str,
        date: str,
        time: str,
        price: str
    ) -> bool:
        """Send new appointment notification to master."""
        return cls.send_email(
            subject=f"Новая запись - {client_name}",
            template_name="new_appointment_master",
            context={
                'master_name': master_name,
                'client_name': client_name,
                'service_name': service_name,
                'date': date,
                'time': time,
                'price': price,
            },
            to_emails=[master_email]
        )

    @classmethod
    def send_review_notification(
        cls,
        master_email: str,
        master_name: str,
        client_name: str,
        rating: int,
        comment: str = ""
    ) -> bool:
        """Send new review notification to master."""
        return cls.send_email(
            subject=f"Новый отзыв от {client_name}",
            template_name="new_review",
            context={
                'master_name': master_name,
                'client_name': client_name,
                'rating': rating,
                'comment': comment,
            },
            to_emails=[master_email]
        )
