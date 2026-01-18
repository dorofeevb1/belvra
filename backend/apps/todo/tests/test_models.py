import pytest

from apps.todo.models import TodoItem
from apps.users.models import User

from .factories import DoneTodoFactory, HighPriorityTodoFactory, TodoItemFactory


@pytest.mark.django_db
class TestTodoItemModel:
    def test_create_todo(self):
        todo = TodoItemFactory()
        assert todo.pk is not None
        assert todo.status == TodoItem.Status.TODO
        assert todo.priority == TodoItem.Priority.MEDIUM

    def test_todo_str(self):
        todo = TodoItemFactory(title="Test task")
        assert "Test task" in str(todo)
        assert todo.master.user.full_name in str(todo)

    def test_todo_default_status(self):
        todo = TodoItemFactory()
        assert todo.status == TodoItem.Status.TODO

    def test_todo_default_priority(self):
        todo = TodoItemFactory()
        assert todo.priority == TodoItem.Priority.MEDIUM

    def test_todo_status_choices(self):
        todo = TodoItemFactory()

        todo.status = TodoItem.Status.IN_PROGRESS
        todo.save()
        assert todo.status == TodoItem.Status.IN_PROGRESS

        todo.status = TodoItem.Status.DONE
        todo.save()
        assert todo.status == TodoItem.Status.DONE

    def test_todo_priority_choices(self):
        todo = TodoItemFactory()

        todo.priority = TodoItem.Priority.LOW
        todo.save()
        assert todo.priority == TodoItem.Priority.LOW

        todo.priority = TodoItem.Priority.HIGH
        todo.save()
        assert todo.priority == TodoItem.Priority.HIGH

    def test_todo_optional_time(self):
        todo = TodoItemFactory(time=None)
        assert todo.time is None

        from datetime import time
        todo.time = time(10, 30)
        todo.save()
        assert todo.time == time(10, 30)

    def test_todo_belongs_to_master(self):
        todo = TodoItemFactory()
        assert todo.master is not None
        assert todo.master.user.role == User.Role.MASTER
