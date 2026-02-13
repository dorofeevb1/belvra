from celery import shared_task
from django.utils import timezone


@shared_task
def close_overdue_todos():
    """Автозакрытие просроченных задач (на прошлые даты и сегодняшних с прошедшим временем)."""
    from .models import TodoItem

    today = timezone.localdate()
    now = timezone.localtime().time()
    active_statuses = [TodoItem.Status.TODO, TodoItem.Status.IN_PROGRESS]

    # Закрываем задачи на прошлые даты
    count = TodoItem.objects.filter(
        date__lt=today,
        status__in=active_statuses
    ).update(status=TodoItem.Status.DONE)

    # Закрываем сегодняшние задачи с прошедшим временем
    count += TodoItem.objects.filter(
        date=today,
        time__isnull=False,
        time__lt=now,
        status__in=active_statuses
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
