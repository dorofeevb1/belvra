from django.db import models

from apps.core.models import BaseModel
from apps.users.models import MasterProfile


class TodoItem(BaseModel):
    """Todo item for masters."""

    class Status(models.TextChoices):
        TODO = "todo", "К выполнению"
        IN_PROGRESS = "in_progress", "В процессе"
        DONE = "done", "Готово"

    class Priority(models.TextChoices):
        LOW = "low", "Низкий"
        MEDIUM = "medium", "Средний"
        HIGH = "high", "Высокий"

    master = models.ForeignKey(
        MasterProfile,
        on_delete=models.CASCADE,
        related_name="todos",
        verbose_name="Мастер"
    )
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    description = models.TextField(blank=True, verbose_name="Описание")
    date = models.DateField(verbose_name="Дата")
    time = models.TimeField(null=True, blank=True, verbose_name="Время")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO,
        verbose_name="Статус"
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        verbose_name="Приоритет"
    )

    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["master", "date"]),
            models.Index(fields=["master", "status"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.master.user.full_name}"
