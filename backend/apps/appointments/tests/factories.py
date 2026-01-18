from datetime import date, time, timedelta

import factory
from faker import Faker

from apps.appointments.models import Appointment, Review, WorkSchedule
from apps.services.tests.factories import ServiceFactory
from apps.users.tests.factories import MasterProfileFactory, UserFactory

fake = Faker("ru_RU")


class WorkScheduleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkSchedule

    master = factory.SubFactory(MasterProfileFactory)
    weekday = factory.LazyAttribute(lambda _: fake.random_int(min=0, max=6))
    start_time = time(9, 0)
    end_time = time(18, 0)
    is_working = True


class AppointmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Appointment

    client = factory.SubFactory(UserFactory)
    master = factory.SubFactory(MasterProfileFactory)
    service = factory.SubFactory(ServiceFactory)
    date = factory.LazyAttribute(lambda _: date.today() + timedelta(days=fake.random_int(min=1, max=14)))
    start_time = factory.LazyAttribute(lambda _: time(fake.random_int(min=9, max=16), 0))
    end_time = factory.LazyAttribute(lambda obj: time(obj.start_time.hour + 1, 0))
    status = Appointment.Status.PENDING
    price = factory.LazyAttribute(lambda _: fake.pydecimal(left_digits=4, right_digits=2, min_value=500, max_value=10000))
    notes = ""


class ConfirmedAppointmentFactory(AppointmentFactory):
    status = Appointment.Status.CONFIRMED


class CompletedAppointmentFactory(AppointmentFactory):
    status = Appointment.Status.COMPLETED
    date = factory.LazyAttribute(lambda _: date.today() - timedelta(days=fake.random_int(min=1, max=30)))


class ReviewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Review

    appointment = factory.SubFactory(CompletedAppointmentFactory)
    rating = factory.LazyAttribute(lambda _: fake.random_int(min=1, max=5))
    comment = factory.LazyAttribute(lambda _: fake.text(max_nb_chars=200))
