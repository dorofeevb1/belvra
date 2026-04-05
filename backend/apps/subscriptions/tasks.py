"""
Celery tasks for subscription management.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def check_expiring_subscriptions():
    """
    Check for subscriptions expiring in 3 days and send notifications.
    Should run daily.
    """
    from apps.core.notifications import NotificationService

    from .models import Subscription

    # Find subscriptions expiring in 3 days
    expiry_date = timezone.now() + timedelta(days=3)
    expiry_start = expiry_date.replace(hour=0, minute=0, second=0, microsecond=0)
    expiry_end = expiry_date.replace(hour=23, minute=59, second=59, microsecond=999999)

    subscriptions = Subscription.objects.filter(
        status=Subscription.Status.ACTIVE,
        current_period_end__gte=expiry_start,
        current_period_end__lte=expiry_end,
        auto_renew=False  # Only notify if auto-renew is off
    ).select_related("user", "plan")

    sent_count = 0
    for subscription in subscriptions:
        try:
            NotificationService.create_notification(
                user=subscription.user,
                notification_type="subscription_expiring",
                title="Подписка скоро истекает",
                message=f"Ваша подписка {subscription.plan.name} истекает {subscription.current_period_end.strftime('%d.%m.%Y')}. Продлите подписку, чтобы сохранить доступ ко всем функциям.",
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Error sending expiring notification for subscription {subscription.id}: {e}")

    return f"Sent {sent_count} expiring subscription notifications"


@shared_task
def renew_subscriptions():
    """
    Attempt to renew subscriptions that are due for renewal.
    Should run daily.
    """
    from .models import Subscription
    from .services import SubscriptionService

    now = timezone.now()

    # Find subscriptions that need renewal (ending today or already past due)
    subscriptions = Subscription.objects.filter(
        status__in=[Subscription.Status.ACTIVE, Subscription.Status.PAST_DUE],
        current_period_end__lte=now,
        auto_renew=True,
        cancel_at_period_end=False,
        tbank_rebill_id__isnull=False
    ).exclude(
        tbank_rebill_id=""
    ).select_related("user", "plan")

    service = SubscriptionService()
    renewed_count = 0
    failed_count = 0

    for subscription in subscriptions:
        try:
            payment = service.renew_subscription(subscription)
            if payment and payment.status == "succeeded":
                renewed_count += 1
            else:
                failed_count += 1
        except Exception as e:
            logger.error(f"Error renewing subscription {subscription.id}: {e}")
            failed_count += 1

    return f"Renewed {renewed_count} subscriptions, failed: {failed_count}"


@shared_task
def expire_subscriptions():
    """
    Mark expired subscriptions as expired.
    Should run daily.
    """
    from .models import Subscription
    from .services import SubscriptionService

    now = timezone.now()

    # Find subscriptions that have expired and are not auto-renewing
    subscriptions = Subscription.objects.filter(
        status=Subscription.Status.ACTIVE,
        current_period_end__lt=now
    ).filter(
        # Either auto_renew is off, or cancel_at_period_end is true, or no payment method saved
        auto_renew=False
    ) | Subscription.objects.filter(
        status=Subscription.Status.ACTIVE,
        current_period_end__lt=now,
        cancel_at_period_end=True
    )

    service = SubscriptionService()
    expired_count = 0

    for subscription in subscriptions:
        try:
            service.expire_subscription(subscription)
            expired_count += 1
        except Exception as e:
            logger.error(f"Error expiring subscription {subscription.id}: {e}")

    return f"Expired {expired_count} subscriptions"


@shared_task
def downgrade_to_free():
    """
    Downgrade expired subscriptions to free plan.
    Should run daily after expire_subscriptions.
    """
    from .models import Subscription
    from .services import SubscriptionService

    # Find expired subscriptions that should be downgraded
    subscriptions = Subscription.objects.filter(
        status=Subscription.Status.EXPIRED
    ).exclude(
        plan__tier="free"
    ).select_related("user", "plan")

    service = SubscriptionService()
    downgraded_count = 0

    for subscription in subscriptions:
        try:
            service.downgrade_to_free(subscription)
            downgraded_count += 1
        except Exception as e:
            logger.error(f"Error downgrading subscription {subscription.id}: {e}")

    return f"Downgraded {downgraded_count} subscriptions to free"


@shared_task
def reset_monthly_usage():
    """
    Reset monthly usage counters for all subscriptions.
    Should run on the 1st of each month.
    """
    from .models import Subscription

    today = timezone.now().date()

    # Reset subscriptions where last_usage_reset is in the previous month
    subscriptions = Subscription.objects.filter(
        status=Subscription.Status.ACTIVE
    ).exclude(
        last_usage_reset=today
    )

    reset_count = 0
    for subscription in subscriptions:
        # Only reset if we're in a new month compared to last reset
        if subscription.last_usage_reset is None or subscription.last_usage_reset.month != today.month:
            subscription.reset_monthly_usage()
            reset_count += 1

    return f"Reset usage for {reset_count} subscriptions"


@shared_task
def notify_past_due_subscriptions():
    """
    Send notifications for subscriptions with failed recurring payments.
    Should run daily.
    """
    from apps.core.notifications import NotificationService

    from .models import Subscription

    subscriptions = Subscription.objects.filter(
        status=Subscription.Status.PAST_DUE
    ).select_related("user", "plan")

    sent_count = 0
    for subscription in subscriptions:
        try:
            NotificationService.create_notification(
                user=subscription.user,
                notification_type="subscription_past_due",
                title="Проблема с оплатой подписки",
                message="Не удалось продлить вашу подписку. Пожалуйста, обновите способ оплаты.",
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Error sending past due notification for subscription {subscription.id}: {e}")

    return f"Sent {sent_count} past due notifications"
