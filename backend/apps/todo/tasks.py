from celery import shared_task
from django.utils import timezone


@shared_task
def close_overdue_todos():
    """Автозакрытие просроченных задач (на прошлые даты)."""
    from .models import TodoItem

    today = timezone.localdate()
    count = TodoItem.objects.filter(
        date__lt=today,
        status__in=[TodoItem.Status.TODO, TodoItem.Status.IN_PROGRESS]
    ).update(status=TodoItem.Status.DONE)

    return f"Auto-closed {count} overdue todos"


@shared_task
def cleanup_old_notifications():
    """Удаление прочитанных уведомлений старше 30 дней."""
    from apps.core.models import Notification

    cutoff = timezone.now() - timezone.timedelta(days=30)
    deleted, _ = Notification.objects.filter(
        is_read=True,
        read_at__lt=cutoff
    ).delete()

    return f"Deleted {deleted} old read notifications"
