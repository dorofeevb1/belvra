from django.conf import settings
from django.db import models

from apps.core.models import BaseModel
from apps.users.models import MasterProfile


class Chat(BaseModel):
    """Chat between master and client."""

    master = models.ForeignKey(
        MasterProfile,
        on_delete=models.CASCADE,
        related_name="chats",
        verbose_name="Мастер"
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="client_chats",
        verbose_name="Клиент"
    )
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    class Meta:
        verbose_name = "Чат"
        verbose_name_plural = "Чаты"
        ordering = ["-updated_at"]
        unique_together = ["master", "client"]

    def __str__(self):
        return f"Чат: {self.master.user.full_name} - {self.client.full_name}"

    @property
    def last_message(self):
        """Get last message in chat."""
        return self.messages.first()

    @property
    def unread_count_for_master(self):
        """Count unread messages for master."""
        return self.messages.filter(
            sender_role=ChatMessage.SenderRole.CLIENT,
            is_read=False
        ).count()

    @property
    def unread_count_for_client(self):
        """Count unread messages for client."""
        return self.messages.filter(
            sender_role=ChatMessage.SenderRole.MASTER,
            is_read=False
        ).count()


class ChatMessage(BaseModel):
    """Message in a chat."""

    class SenderRole(models.TextChoices):
        MASTER = "master", "Мастер"
        CLIENT = "client", "Клиент"

    class MessageType(models.TextChoices):
        TEXT = "text", "Текст"
        IMAGE = "image", "Изображение"
        FILE = "file", "Файл"
        AUDIO = "audio", "Аудио"

    chat = models.ForeignKey(
        Chat,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="Чат"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
        verbose_name="Отправитель"
    )
    sender_role = models.CharField(
        max_length=10,
        choices=SenderRole.choices,
        verbose_name="Роль отправителя"
    )
    content = models.TextField(blank=True, verbose_name="Содержание")
    message_type = models.CharField(
        max_length=10,
        choices=MessageType.choices,
        default=MessageType.TEXT,
        verbose_name="Тип сообщения"
    )
    file = models.FileField(
        upload_to="chat/files/%Y/%m/",
        null=True,
        blank=True,
        verbose_name="Файл"
    )
    is_read = models.BooleanField(default=False, verbose_name="Прочитано")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="Время прочтения")
    reply_to = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='replies',
        verbose_name="Ответ на сообщение"
    )

    class Meta:
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["chat", "-created_at"]),
            models.Index(fields=["sender", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.sender.full_name}: {self.content[:50] or '[файл]'}"

    def mark_as_read(self):
        """Mark message as read."""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at", "updated_at"])
