from datetime import date, timedelta

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.todo.models import TodoItem
from apps.users.tests.factories import MasterUserFactory, UserFactory

from .factories import (
    DoneTodoFactory,
    HighPriorityTodoFactory,
    InProgressTodoFactory,
    OverdueTodoFactory,
    TodayTodoFactory,
    TodoItemFactory,
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
class TestTodoListAPI:
    def test_list_todos_as_master(self, master_client, master_user):
        master_profile = master_user.master_profile
        TodoItemFactory.create_batch(5, master=master_profile)
        TodoItemFactory.create_batch(3)  # Other master's todos

        url = reverse("todo-list")
        response = master_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 5

    def test_list_todos_as_client(self, authenticated_client):
        # Clients should not see any todos (they don't have master profile)
        TodoItemFactory.create_batch(3)

        url = reverse("todo-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 0

    def test_list_todos_unauthenticated(self, api_client):
        url = reverse("todo-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_filter_by_status(self, master_client, master_user):
        master_profile = master_user.master_profile
        TodoItemFactory.create_batch(3, master=master_profile, status=TodoItem.Status.TODO)
        InProgressTodoFactory.create_batch(2, master=master_profile)
        DoneTodoFactory.create_batch(1, master=master_profile)

        url = reverse("todo-list")
        response = master_client.get(url, {"status": "in_progress"})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 2
        for todo in response.data["results"]:
            assert todo["status"] == "in_progress"

    def test_filter_by_priority(self, master_client, master_user):
        master_profile = master_user.master_profile
        TodoItemFactory.create_batch(2, master=master_profile, priority=TodoItem.Priority.LOW)
        HighPriorityTodoFactory.create_batch(3, master=master_profile)

        url = reverse("todo-list")
        response = master_client.get(url, {"priority": "high"})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 3
        for todo in response.data["results"]:
            assert todo["priority"] == "high"

    def test_search_todos(self, master_client, master_user):
        master_profile = master_user.master_profile
        TodoItemFactory(master=master_profile, title="Buy supplies")
        TodoItemFactory(master=master_profile, title="Call client")
        TodoItemFactory(master=master_profile, title="Buy equipment")

        url = reverse("todo-list")
        response = master_client.get(url, {"search": "Buy"})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 2


@pytest.mark.django_db
class TestTodoCreateAPI:
    def test_create_todo(self, master_client, master_user):
        url = reverse("todo-list")
        data = {
            "title": "New todo task",
            "description": "Task description",
            "date": (date.today() + timedelta(days=1)).isoformat(),
            "priority": "high"
        }
        response = master_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == "New todo task"
        assert response.data["priority"] == "high"
        assert TodoItem.objects.filter(master=master_user.master_profile).exists()

    def test_create_todo_as_client_fails(self, authenticated_client):
        url = reverse("todo-list")
        data = {
            "title": "New todo task",
            "date": date.today().isoformat()
        }
        # Client doesn't have master_profile, so create should raise ValueError
        # which becomes a 500 Internal Server Error
        import pytest
        with pytest.raises(ValueError, match="User must have a master profile"):
            authenticated_client.post(url, data)

    def test_create_todo_with_time(self, master_client, master_user):
        url = reverse("todo-list")
        data = {
            "title": "Meeting with client",
            "date": date.today().isoformat(),
            "time": "14:30"
        }
        response = master_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["time"] == "14:30:00"


@pytest.mark.django_db
class TestTodoDetailAPI:
    def test_get_todo_detail(self, master_client, master_user):
        master_profile = master_user.master_profile
        todo = TodoItemFactory(master=master_profile)

        url = reverse("todo-detail", kwargs={"pk": todo.pk})
        response = master_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(todo.pk)
        assert response.data["title"] == todo.title

    def test_get_other_master_todo(self, master_client):
        # Todo belongs to other master
        todo = TodoItemFactory()

        url = reverse("todo-detail", kwargs={"pk": todo.pk})
        response = master_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestTodoUpdateAPI:
    def test_update_todo(self, master_client, master_user):
        master_profile = master_user.master_profile
        todo = TodoItemFactory(master=master_profile, title="Old title")

        url = reverse("todo-detail", kwargs={"pk": todo.pk})
        data = {"title": "Updated title", "date": todo.date.isoformat()}
        response = master_client.put(url, data)

        assert response.status_code == status.HTTP_200_OK
        todo.refresh_from_db()
        assert todo.title == "Updated title"

    def test_partial_update_todo(self, master_client, master_user):
        master_profile = master_user.master_profile
        todo = TodoItemFactory(master=master_profile, priority=TodoItem.Priority.LOW)

        url = reverse("todo-detail", kwargs={"pk": todo.pk})
        data = {"priority": "high"}
        response = master_client.patch(url, data)

        assert response.status_code == status.HTTP_200_OK
        todo.refresh_from_db()
        assert todo.priority == TodoItem.Priority.HIGH


@pytest.mark.django_db
class TestTodoDeleteAPI:
    def test_delete_todo(self, master_client, master_user):
        master_profile = master_user.master_profile
        todo = TodoItemFactory(master=master_profile)
        todo_id = todo.pk

        url = reverse("todo-detail", kwargs={"pk": todo.pk})
        response = master_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not TodoItem.objects.filter(pk=todo_id).exists()


@pytest.mark.django_db
class TestTodoUpdateStatusAPI:
    def test_update_status(self, master_client, master_user):
        master_profile = master_user.master_profile
        todo = TodoItemFactory(master=master_profile, status=TodoItem.Status.TODO)

        url = reverse("todo-update-status", kwargs={"pk": todo.pk})
        data = {"status": "in_progress"}
        response = master_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        todo.refresh_from_db()
        assert todo.status == TodoItem.Status.IN_PROGRESS

    def test_update_status_to_done(self, master_client, master_user):
        master_profile = master_user.master_profile
        todo = TodoItemFactory(master=master_profile, status=TodoItem.Status.IN_PROGRESS)

        url = reverse("todo-update-status", kwargs={"pk": todo.pk})
        data = {"status": "done"}
        response = master_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        todo.refresh_from_db()
        assert todo.status == TodoItem.Status.DONE


@pytest.mark.django_db
class TestTodoByDateAPI:
    def test_get_todos_by_date(self, master_client, master_user):
        master_profile = master_user.master_profile
        target_date = date.today() + timedelta(days=1)
        TodoItemFactory.create_batch(3, master=master_profile, date=target_date)
        TodoItemFactory.create_batch(2, master=master_profile, date=date.today())

        url = reverse("todo-by-date", kwargs={"date": target_date.isoformat()})
        response = master_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3


@pytest.mark.django_db
class TestTodoTodayAPI:
    def test_get_today_todos(self, master_client, master_user):
        master_profile = master_user.master_profile
        TodayTodoFactory.create_batch(4, master=master_profile)
        TodoItemFactory.create_batch(2, master=master_profile, date=date.today() + timedelta(days=1))

        url = reverse("todo-today")
        response = master_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 4


@pytest.mark.django_db
class TestTodoStatsAPI:
    def test_get_stats(self, master_client, master_user):
        master_profile = master_user.master_profile

        # Create various todos
        TodoItemFactory.create_batch(3, master=master_profile, status=TodoItem.Status.TODO)
        InProgressTodoFactory.create_batch(2, master=master_profile)
        DoneTodoFactory.create_batch(5, master=master_profile)
        TodayTodoFactory.create_batch(2, master=master_profile, status=TodoItem.Status.TODO)
        TodayTodoFactory(master=master_profile, status=TodoItem.Status.DONE)
        OverdueTodoFactory.create_batch(2, master=master_profile)

        url = reverse("todo-stats")
        response = master_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total"] >= 10
        assert response.data["todo"] >= 3
        assert response.data["in_progress"] >= 2
        assert response.data["done"] >= 5
        assert "today_total" in response.data
        assert "today_done" in response.data
        assert "overdue" in response.data
