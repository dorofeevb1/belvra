"""
Tests for appointment Celery tasks.
"""

from datetime import date, time, timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.appointments.tasks import (
    cleanup_old_appointments,
    mark_no_show_appointments,
    send_completion_reminder,
)

from .factories import AppointmentFactory, ConfirmedAppointmentFactory


@pytest.mark.django_db
class TestMarkNoShowAppointments:
    """Tests for mark_no_show_appointments task."""

    def test_mark_past_days_confirmed_as_no_show(self):
        """Confirmed appointments from past days should be marked as no-show."""
        yesterday = date.today() - timedelta(days=1)

        # Past day confirmed appointment - should be marked no-show
        appt1 = AppointmentFactory(
            date=yesterday,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=Appointment.Status.CONFIRMED
        )

        # Past day completed - should NOT be changed
        appt2 = AppointmentFactory(
            date=yesterday,
            status=Appointment.Status.COMPLETED
        )

        result = mark_no_show_appointments()

        appt1.refresh_from_db()
        appt2.refresh_from_db()

        assert appt1.status == Appointment.Status.NO_SHOW
        assert appt2.status == Appointment.Status.COMPLETED
        assert "1" in result or "past days: 1" in result

    def test_mark_today_past_end_time_as_no_show(self):
        """Today's confirmed appointments past end_time should be marked as no-show."""
        today = date.today()
        now = timezone.now()

        # Calculate times - one in the past, one in the future
        past_end_time = (now - timedelta(hours=2)).time()
        future_end_time = (now + timedelta(hours=2)).time()

        # Today appointment with past end_time - should be marked no-show
        appt_past = AppointmentFactory(
            date=today,
            start_time=time(0, 0),
            end_time=past_end_time,
            status=Appointment.Status.CONFIRMED
        )

        # Today appointment with future end_time - should NOT be changed
        appt_future = AppointmentFactory(
            date=today,
            start_time=time(0, 0),
            end_time=future_end_time,
            status=Appointment.Status.CONFIRMED
        )

        result = mark_no_show_appointments()

        appt_past.refresh_from_db()
        appt_future.refresh_from_db()

        assert appt_past.status == Appointment.Status.NO_SHOW
        assert appt_future.status == Appointment.Status.CONFIRMED

    def test_does_not_mark_archived_appointments(self):
        """Archived appointments should not be marked as no-show."""
        yesterday = date.today() - timedelta(days=1)

        appt = AppointmentFactory(
            date=yesterday,
            status=Appointment.Status.CONFIRMED,
            is_archived=True
        )

        mark_no_show_appointments()

        appt.refresh_from_db()
        assert appt.status == Appointment.Status.CONFIRMED

    def test_does_not_mark_pending_appointments(self):
        """Pending appointments should not be marked as no-show (only confirmed)."""
        yesterday = date.today() - timedelta(days=1)

        appt = AppointmentFactory(
            date=yesterday,
            status=Appointment.Status.PENDING
        )

        mark_no_show_appointments()

        appt.refresh_from_db()
        assert appt.status == Appointment.Status.PENDING


@pytest.mark.django_db
class TestCleanupOldAppointments:
    """Tests for cleanup_old_appointments task."""

    def test_archives_old_completed_appointments(self):
        """Appointments older than 365 days should be archived (soft delete)."""
        old_date = date.today() - timedelta(days=400)

        appt = AppointmentFactory(
            date=old_date,
            status=Appointment.Status.COMPLETED,
            is_archived=False
        )

        result = cleanup_old_appointments()

        appt.refresh_from_db()
        assert appt.is_archived is True
        assert "Archived 1" in result

    def test_archives_old_cancelled_appointments(self):
        """Old cancelled appointments should be archived."""
        old_date = date.today() - timedelta(days=400)

        appt = AppointmentFactory(
            date=old_date,
            status=Appointment.Status.CANCELLED,
            is_archived=False
        )

        cleanup_old_appointments()

        appt.refresh_from_db()
        assert appt.is_archived is True

    def test_archives_old_no_show_appointments(self):
        """Old no-show appointments should be archived."""
        old_date = date.today() - timedelta(days=400)

        appt = AppointmentFactory(
            date=old_date,
            status=Appointment.Status.NO_SHOW,
            is_archived=False
        )

        cleanup_old_appointments()

        appt.refresh_from_db()
        assert appt.is_archived is True

    def test_does_not_archive_recent_appointments(self):
        """Appointments less than 365 days old should not be archived."""
        recent_date = date.today() - timedelta(days=100)

        appt = AppointmentFactory(
            date=recent_date,
            status=Appointment.Status.COMPLETED,
            is_archived=False
        )

        cleanup_old_appointments()

        appt.refresh_from_db()
        assert appt.is_archived is False

    def test_does_not_archive_pending_appointments(self):
        """Pending appointments should not be archived regardless of age."""
        old_date = date.today() - timedelta(days=400)

        appt = AppointmentFactory(
            date=old_date,
            status=Appointment.Status.PENDING,
            is_archived=False
        )

        cleanup_old_appointments()

        appt.refresh_from_db()
        assert appt.is_archived is False

    def test_does_not_re_archive_already_archived(self):
        """Already archived appointments should not be processed again."""
        old_date = date.today() - timedelta(days=400)

        appt = AppointmentFactory(
            date=old_date,
            status=Appointment.Status.COMPLETED,
            is_archived=True
        )

        result = cleanup_old_appointments()

        # Should report 0 archived since it was already archived
        assert "Archived 0" in result


@pytest.mark.django_db
class TestSendCompletionReminder:
    """Tests for send_completion_reminder task."""

    @patch("apps.core.notifications.NotificationService.create_notification")
    def test_sends_reminder_for_appointments_ended_1_hour_ago(self, mock_create_notification):
        """Reminders should be sent for confirmed appointments that ended ~1 hour ago."""
        today = date.today()
        now = timezone.now()

        # Calculate end_time that was about 1 hour ago
        one_hour_ago = (now - timedelta(hours=1, minutes=2)).time()

        appt = ConfirmedAppointmentFactory(
            date=today,
            start_time=time(0, 0),
            end_time=one_hour_ago,
            status=Appointment.Status.CONFIRMED,
            is_archived=False
        )

        result = send_completion_reminder()

        # Verify notification was attempted
        assert mock_create_notification.called or "1" in result

    @patch("apps.core.notifications.NotificationService.create_notification")
    def test_does_not_send_reminder_for_completed_appointments(self, mock_create_notification):
        """No reminder for already completed appointments."""
        today = date.today()
        now = timezone.now()
        one_hour_ago = (now - timedelta(hours=1, minutes=2)).time()

        appt = AppointmentFactory(
            date=today,
            start_time=time(0, 0),
            end_time=one_hour_ago,
            status=Appointment.Status.COMPLETED,
            is_archived=False
        )

        result = send_completion_reminder()

        assert "0" in result


@pytest.mark.django_db
class TestIsArchivedField:
    """Tests for the is_archived field functionality."""

    def test_default_is_archived_false(self):
        """New appointments should have is_archived=False by default."""
        appt = AppointmentFactory()
        assert appt.is_archived is False

    def test_can_set_is_archived(self):
        """is_archived field should be settable."""
        appt = AppointmentFactory(is_archived=True)
        assert appt.is_archived is True

    def test_archived_appointments_excluded_from_queryset(self):
        """Archived appointments should be excluded when filtered."""
        AppointmentFactory(is_archived=False)
        AppointmentFactory(is_archived=True)

        non_archived = Appointment.objects.filter(is_archived=False)
        all_appointments = Appointment.objects.all()

        assert non_archived.count() == 1
        assert all_appointments.count() == 2
