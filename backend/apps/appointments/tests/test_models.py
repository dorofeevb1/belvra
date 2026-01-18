from datetime import date, time, timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.appointments.models import Appointment, Review, WorkSchedule

from .factories import (
    AppointmentFactory,
    CompletedAppointmentFactory,
    ConfirmedAppointmentFactory,
    ReviewFactory,
    WorkScheduleFactory,
)


@pytest.mark.django_db
class TestWorkScheduleModel:
    def test_create_schedule(self):
        schedule = WorkScheduleFactory()
        assert schedule.pk is not None
        assert schedule.master is not None

    def test_schedule_str(self):
        schedule = WorkScheduleFactory(weekday=0)  # Понедельник
        assert schedule.master.user.full_name in str(schedule)

    def test_unique_together_constraint(self):
        schedule = WorkScheduleFactory(weekday=1)

        with pytest.raises(Exception):
            WorkScheduleFactory(master=schedule.master, weekday=1)


@pytest.mark.django_db
class TestAppointmentModel:
    def test_create_appointment(self):
        appointment = AppointmentFactory()
        assert appointment.pk is not None
        assert appointment.client is not None
        assert appointment.master is not None
        assert appointment.service is not None

    def test_appointment_str(self):
        appointment = AppointmentFactory()
        result = str(appointment)
        assert appointment.client.full_name in result
        assert appointment.master.user.full_name in result

    def test_appointment_default_status(self):
        appointment = AppointmentFactory()
        assert appointment.status == Appointment.Status.PENDING

    def test_appointment_is_past(self):
        past_appointment = AppointmentFactory(
            date=date.today() - timedelta(days=1),
            end_time=time(10, 0)
        )
        future_appointment = AppointmentFactory(
            date=date.today() + timedelta(days=1)
        )

        assert past_appointment.is_past is True
        assert future_appointment.is_past is False

    def test_appointment_can_cancel_pending(self):
        # Запись на завтра можно отменить
        appointment = AppointmentFactory(
            date=date.today() + timedelta(days=1),
            start_time=time(12, 0),
            status=Appointment.Status.PENDING
        )
        assert appointment.can_cancel is True

    def test_appointment_can_cancel_confirmed(self):
        # Подтверждённую запись на завтра можно отменить
        appointment = ConfirmedAppointmentFactory(
            date=date.today() + timedelta(days=1),
            start_time=time(12, 0)
        )
        assert appointment.can_cancel is True

    def test_appointment_cannot_cancel_completed(self):
        appointment = CompletedAppointmentFactory()
        assert appointment.can_cancel is False

    def test_appointment_cannot_cancel_already_cancelled(self):
        appointment = AppointmentFactory(status=Appointment.Status.CANCELLED)
        assert appointment.can_cancel is False


@pytest.mark.django_db
class TestReviewModel:
    def test_create_review(self):
        review = ReviewFactory()
        assert review.pk is not None
        assert review.appointment.status == Appointment.Status.COMPLETED

    def test_review_str(self):
        review = ReviewFactory()
        assert review.appointment.client.full_name in str(review)

    def test_review_rating_range(self):
        review = ReviewFactory(rating=5)
        assert 1 <= review.rating <= 5

    def test_review_updates_master_rating(self):
        """Тест что отзыв обновляет рейтинг мастера"""
        appointment = CompletedAppointmentFactory()
        master = appointment.master

        # Изначальный рейтинг 0
        initial_reviews = master.reviews_count

        review = Review.objects.create(
            appointment=appointment,
            rating=5,
            comment="Отлично!"
        )

        master.refresh_from_db()
        assert master.reviews_count == initial_reviews + 1
        assert master.rating > 0

    def test_review_one_per_appointment(self):
        """Один отзыв на одну запись"""
        review = ReviewFactory()

        with pytest.raises(Exception):
            ReviewFactory(appointment=review.appointment)
