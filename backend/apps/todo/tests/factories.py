from datetime import date, timedelta

import factory
from faker import Faker

from apps.todo.models import TodoItem
from apps.users.tests.factories import MasterProfileFactory

fake = Faker("ru_RU")


class TodoItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TodoItem

    master = factory.SubFactory(MasterProfileFactory)
    title = factory.LazyAttribute(lambda _: fake.sentence(nb_words=4))
    description = factory.LazyAttribute(lambda _: fake.text(max_nb_chars=200))
    date = factory.LazyAttribute(lambda _: date.today() + timedelta(days=fake.random_int(min=0, max=7)))
    time = factory.LazyAttribute(lambda _: None)
    status = TodoItem.Status.TODO
    priority = TodoItem.Priority.MEDIUM


class InProgressTodoFactory(TodoItemFactory):
    status = TodoItem.Status.IN_PROGRESS


class DoneTodoFactory(TodoItemFactory):
    status = TodoItem.Status.DONE


class TodayTodoFactory(TodoItemFactory):
    date = factory.LazyAttribute(lambda _: date.today())


class OverdueTodoFactory(TodoItemFactory):
    date = factory.LazyAttribute(lambda _: date.today() - timedelta(days=fake.random_int(min=1, max=30)))
    status = TodoItem.Status.TODO


class HighPriorityTodoFactory(TodoItemFactory):
    priority = TodoItem.Priority.HIGH


class LowPriorityTodoFactory(TodoItemFactory):
    priority = TodoItem.Priority.LOW
