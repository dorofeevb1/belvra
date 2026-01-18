from datetime import date, time, timedelta

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.appointments.models import Appointment
from apps.services.tests.factories import MasterServiceFactory, ServiceFactory
from apps.users.tests.factories import MasterProfileFactory, MasterUserFactory, UserFactory

from .factories import (
    AppointmentFactory,
    CompletedAppointmentFactory,
    ConfirmedAppointmentFactory,
    ReviewFactory,
    WorkScheduleFactory,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def master_user(db):
    return MasterUserFactory()


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def master_client(api_client, master_user):
    api_client.force_authenticate(user=master_user)
    return api_client


@pytest.mark.django_db
class TestAppointmentAPI:
    def test_list_appointments_authenticated(self, authenticated_client, user):
        AppointmentFactory.create_batch(3, client=user)
        AppointmentFactory.create_batch(2)  # Чужие записи

        url = reverse("appointment-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Видит только свои записи
        assert len(response.data["results"]) == 3

    def test_list_appointments_unauthenticated(self, api_client):
        url = reverse("appointment-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_appointment(self, authenticated_client, user):
        master_profile = MasterProfileFactory()
        service = ServiceFactory()
        MasterServiceFactory(master=master_profile, service=service)

        # Создаём расписание на нужный день
        target_date = date.today() + timedelta(days=1)
        WorkScheduleFactory(
            master=master_profile,
            weekday=target_date.weekday(),
            start_time=time(9, 0),
            end_time=time(18, 0)
        )

        url = reverse("appointment-list")
        data = {
            "master_id": str(master_profile.pk),
            "service_id": str(service.pk),
            "date": target_date.isoformat(),
            "start_time": "10:00",
            "notes": "Тестовая запись"
        }
        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert Appointment.objects.filter(client=user).exists()

    def test_create_appointment_master_not_working(self, authenticated_client):
        master_profile = MasterProfileFactory()
        service = ServiceFactory()
        MasterServiceFactory(master=master_profile, service=service)

        # Нет расписания на этот день
        target_date = date.today() + timedelta(days=1)

        url = reverse("appointment-list")
        data = {
            "master_id": str(master_profile.pk),
            "service_id": str(service.pk),
            "date": target_date.isoformat(),
            "start_time": "10:00"
        }
        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cancel_appointment(self, authenticated_client, user):
        appointment = AppointmentFactory(
            client=user,
            date=date.today() + timedelta(days=2),
            start_time=time(14, 0)
        )

        url = reverse("appointment-cancel", kwargs={"pk": appointment.pk})
        response = authenticated_client.post(url, {"reason": "Не могу прийти"})

        assert response.status_code == status.HTTP_200_OK
        appointment.refresh_from_db()
        assert appointment.status == Appointment.Status.CANCELLED

    def test_cannot_cancel_past_appointment(self, authenticated_client, user):
        appointment = AppointmentFactory(
            client=user,
            date=date.today() - timedelta(days=1),
            status=Appointment.Status.COMPLETED
        )

        url = reverse("appointment-cancel", kwargs={"pk": appointment.pk})
        response = authenticated_client.post(url, {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_confirm_appointment_as_master(self, master_client, master_user):
        master_profile = master_user.master_profile
        appointment = AppointmentFactory(
            master=master_profile,
            status=Appointment.Status.PENDING
        )

        url = reverse("appointment-confirm", kwargs={"pk": appointment.pk})
        response = master_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        appointment.refresh_from_db()
        assert appointment.status == Appointment.Status.CONFIRMED

    def test_confirm_appointment_not_master(self, authenticated_client, user):
        # User is client, trying to confirm someone else's appointment
        appointment = AppointmentFactory(
            client=user,  # Make user the client so they can see the appointment
            status=Appointment.Status.PENDING
        )

        url = reverse("appointment-confirm", kwargs={"pk": appointment.pk})
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_complete_appointment_as_master(self, master_client, master_user):
        master_profile = master_user.master_profile
        appointment = ConfirmedAppointmentFactory(master=master_profile)

        url = reverse("appointment-complete", kwargs={"pk": appointment.pk})
        response = master_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        appointment.refresh_from_db()
        assert appointment.status == Appointment.Status.COMPLETED

    def test_upcoming_appointments(self, authenticated_client, user):
        # Будущие записи
        AppointmentFactory(
            client=user,
            date=date.today() + timedelta(days=1),
            status=Appointment.Status.CONFIRMED
        )
        AppointmentFactory(
            client=user,
            date=date.today() + timedelta(days=3),
            status=Appointment.Status.PENDING
        )
        # Прошлая запись
        AppointmentFactory(
            client=user,
            date=date.today() - timedelta(days=1),
            status=Appointment.Status.COMPLETED
        )

        url = reverse("appointment-upcoming")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2


@pytest.mark.django_db
class TestAvailableSlotsAPI:
    def test_get_available_slots(self, api_client):
        master_profile = MasterProfileFactory()
        service = ServiceFactory(duration=60)
        MasterServiceFactory(master=master_profile, service=service)

        target_date = date.today() + timedelta(days=1)
        WorkScheduleFactory(
            master=master_profile,
            weekday=target_date.weekday(),
            start_time=time(9, 0),
            end_time=time(18, 0)
        )

        url = reverse("available-slots")
        data = {
            "master_id": str(master_profile.pk),
            "service_id": str(service.pk),
            "date": target_date.isoformat()
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert "slots" in response.data
        assert len(response.data["slots"]) > 0

    def test_slots_exclude_booked(self, api_client):
        master_profile = MasterProfileFactory()
        service = ServiceFactory(duration=60)
        MasterServiceFactory(master=master_profile, service=service)

        target_date = date.today() + timedelta(days=1)
        WorkScheduleFactory(
            master=master_profile,
            weekday=target_date.weekday(),
            start_time=time(9, 0),
            end_time=time(12, 0)  # Только 3 часа
        )

        # Бронируем 10:00-11:00
        AppointmentFactory(
            master=master_profile,
            date=target_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status=Appointment.Status.CONFIRMED
        )

        url = reverse("available-slots")
        data = {
            "master_id": str(master_profile.pk),
            "service_id": str(service.pk),
            "date": target_date.isoformat()
        }
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        slots = response.data["slots"]
        start_times = [s["start_time"] for s in slots]
        assert "10:00" not in start_times


@pytest.mark.django_db
class TestReviewAPI:
    def test_create_review(self, authenticated_client, user):
        appointment = CompletedAppointmentFactory(client=user)

        url = reverse("review-list")
        data = {
            "appointment": str(appointment.pk),
            "rating": 5,
            "comment": "Отличный мастер!"
        }
        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED

    def test_cannot_review_not_completed(self, authenticated_client, user):
        appointment = ConfirmedAppointmentFactory(client=user)

        url = reverse("review-list")
        data = {
            "appointment": str(appointment.pk),
            "rating": 5,
            "comment": "Хорошо"
        }
        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_review_others_appointment(self, authenticated_client):
        appointment = CompletedAppointmentFactory()  # Чужая запись

        url = reverse("review-list")
        data = {
            "appointment": str(appointment.pk),
            "rating": 5,
            "comment": "Хорошо"
        }
        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_reviews_by_master(self, api_client):
        master_profile = MasterProfileFactory()
        appointment1 = CompletedAppointmentFactory(master=master_profile)
        appointment2 = CompletedAppointmentFactory(master=master_profile)
        ReviewFactory(appointment=appointment1)
        ReviewFactory(appointment=appointment2)
        ReviewFactory()  # Отзыв другому мастеру

        url = reverse("review-by-master", kwargs={"master_id": master_profile.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_invalid_rating(self, authenticated_client, user):
        appointment = CompletedAppointmentFactory(client=user)

        url = reverse("review-list")
        data = {
            "appointment": str(appointment.pk),
            "rating": 10,  # Invalid
            "comment": "Хорошо"
        }
        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
