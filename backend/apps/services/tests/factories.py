import factory
from django.utils.text import slugify
from faker import Faker

from apps.services.models import Category, MasterService, Service
from apps.users.tests.factories import MasterProfileFactory

fake = Faker("ru_RU")


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.LazyAttribute(
        lambda _: fake.random_element([
            "Стрижки", "Окрашивание", "Маникюр", "Педикюр",
            "Массаж", "Косметология", "Эпиляция", "Брови и ресницы"
        ])
    )
    slug = factory.LazyAttribute(lambda obj: slugify(obj.name) + f"-{fake.random_int(1, 9999)}")
    description = factory.LazyAttribute(lambda _: fake.text(max_nb_chars=200))
    is_active = True
    order = factory.Sequence(lambda n: n)


class ServiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Service

    category = factory.SubFactory(CategoryFactory)
    name = factory.LazyAttribute(
        lambda _: fake.random_element([
            "Стрижка женская", "Стрижка мужская", "Окрашивание корней",
            "Мелирование", "Маникюр классический", "Маникюр аппаратный",
            "Массаж спины", "Массаж лица", "Чистка лица"
        ])
    )
    slug = factory.LazyAttribute(lambda obj: slugify(obj.name) + f"-{fake.random_int(1, 9999)}")
    description = factory.LazyAttribute(lambda _: fake.text(max_nb_chars=300))
    price = factory.LazyAttribute(lambda _: fake.pydecimal(left_digits=4, right_digits=2, min_value=500, max_value=10000))
    duration = factory.LazyAttribute(lambda _: fake.random_element([30, 45, 60, 90, 120]))
    is_active = True
    is_popular = factory.LazyAttribute(lambda _: fake.boolean(chance_of_getting_true=30))


class MasterServiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MasterService

    master = factory.SubFactory(MasterProfileFactory)
    service = factory.SubFactory(ServiceFactory)
    price = None
    duration = None
