"""
Celery configuration for BeautyStyleService project.
"""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("beautystyle")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Celery Beat Schedule
app.conf.beat_schedule = {
    "cleanup-expired-tokens": {
        "task": "apps.users.tasks.cleanup_expired_tokens",
        "schedule": crontab(hour=0, minute=0),  # Daily at midnight
    },
    "send-appointment-reminders": {
        "task": "apps.appointments.tasks.send_appointment_reminders",
        "schedule": crontab(hour=8, minute=0),  # Daily at 8 AM
    },
    "cleanup-old-appointments": {
        "task": "apps.appointments.tasks.cleanup_old_appointments",
        "schedule": crontab(day_of_week=0, hour=3, minute=0),  # Weekly on Sunday
    },
    "mark-no-show-appointments": {
        "task": "apps.appointments.tasks.mark_no_show_appointments",
        "schedule": crontab(hour=9, minute=0),  # Daily at 9 AM (after appointments from yesterday)
    },
    # Payment tasks
    "release-held-funds": {
        "task": "apps.payments.tasks.release_held_funds",
        "schedule": crontab(hour="*/1"),  # Every hour
    },
    "process-auto-withdrawals": {
        "task": "apps.payments.tasks.process_auto_withdrawals",
        "schedule": crontab(hour=6, minute=0),  # Daily at 6 AM
    },
    "sync-payment-statuses": {
        "task": "apps.payments.tasks.sync_payment_statuses",
        "schedule": crontab(minute="*/10"),  # Every 10 minutes
    },
    "cleanup-expired-payments": {
        "task": "apps.payments.tasks.cleanup_expired_payments",
        "schedule": crontab(hour="*/2"),  # Every 2 hours
    },
    "generate-daily-payment-report": {
        "task": "apps.payments.tasks.generate_daily_report",
        "schedule": crontab(hour=1, minute=0),  # Daily at 1 AM
    },
    "cleanup-unverified-accounts": {
        "task": "apps.core.tasks.cleanup_unverified_accounts",
        "schedule": crontab(minute="*/1"),  # Every minute
    },
}
