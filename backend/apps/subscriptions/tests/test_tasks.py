"""
Tests for subscription Celery tasks.
"""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.subscriptions.models import Subscription, SubscriptionPlan
from apps.subscriptions.tasks import (
    check_expiring_subscriptions,
    downgrade_to_free,
    expire_subscriptions,
    reset_monthly_usage,
)
from apps.users.tests.factories import MasterUserFactory

from .factories import (
    ActiveSubscriptionFactory,
    ExpiredSubscriptionFactory,
    FreeMasterPlanFactory,
    ProMasterPlanFactory,
)


@pytest.mark.django_db
class TestCheckExpiringSubscriptions:
    """Tests for check_expiring_subscriptions task."""

    @patch("apps.core.notifications.NotificationService.create_notification")
    def test_notifies_expiring_subscriptions(self, mock_create_notification):
        """Should notify users with subscriptions expiring in 3 days."""
        user = MasterUserFactory()
        plan = ProMasterPlanFactory()

        # Subscription expiring in exactly 3 days
        expiring_sub = ActiveSubscriptionFactory(
            user=user,
            plan=plan,
            current_period_end=timezone.now() + timedelta(days=3),
            auto_renew=False
        )

        result = check_expiring_subscriptions()

        assert mock_create_notification.called
        assert "1" in result

    @patch("apps.core.notifications.NotificationService.create_notification")
    def test_does_not_notify_auto_renew_subscriptions(self, mock_create_notification):
        """Should not notify subscriptions with auto_renew enabled."""
        user = MasterUserFactory()
        plan = ProMasterPlanFactory()

        # Subscription expiring but with auto_renew
        sub = ActiveSubscriptionFactory(
            user=user,
            plan=plan,
            current_period_end=timezone.now() + timedelta(days=3),
            auto_renew=True
        )

        result = check_expiring_subscriptions()

        assert not mock_create_notification.called
        assert "0" in result

    @patch("apps.core.notifications.NotificationService.create_notification")
    def test_does_not_notify_not_expiring_soon(self, mock_create_notification):
        """Should not notify subscriptions not expiring soon."""
        user = MasterUserFactory()
        plan = ProMasterPlanFactory()

        # Subscription expiring in 10 days
        sub = ActiveSubscriptionFactory(
            user=user,
            plan=plan,
            current_period_end=timezone.now() + timedelta(days=10),
            auto_renew=False
        )

        result = check_expiring_subscriptions()

        assert not mock_create_notification.called


@pytest.mark.django_db
class TestExpireSubscriptions:
    """Tests for expire_subscriptions task."""

    @patch("apps.subscriptions.services.SubscriptionService.expire_subscription")
    def test_expires_subscriptions_past_end_date(self, mock_expire):
        """Should expire subscriptions past their end date with auto_renew off."""
        user = MasterUserFactory()
        plan = ProMasterPlanFactory()

        sub = ActiveSubscriptionFactory(
            user=user,
            plan=plan,
            current_period_end=timezone.now() - timedelta(days=1),
            auto_renew=False
        )

        expire_subscriptions()

        mock_expire.assert_called()

    @patch("apps.subscriptions.services.SubscriptionService.expire_subscription")
    def test_expires_cancelled_at_period_end(self, mock_expire):
        """Should expire subscriptions marked cancel_at_period_end past end date."""
        user = MasterUserFactory()
        plan = ProMasterPlanFactory()

        sub = ActiveSubscriptionFactory(
            user=user,
            plan=plan,
            current_period_end=timezone.now() - timedelta(days=1),
            cancel_at_period_end=True
        )

        expire_subscriptions()

        mock_expire.assert_called()


@pytest.mark.django_db
class TestDowngradeToFree:
    """Tests for downgrade_to_free task."""

    @patch("apps.subscriptions.services.SubscriptionService.downgrade_to_free")
    def test_downgrades_expired_subscriptions(self, mock_downgrade):
        """Should downgrade expired pro subscriptions to free."""
        user = MasterUserFactory()
        pro_plan = ProMasterPlanFactory()
        FreeMasterPlanFactory()  # Ensure free plan exists

        sub = ExpiredSubscriptionFactory(
            user=user,
            plan=pro_plan
        )

        downgrade_to_free()

        mock_downgrade.assert_called()

    @patch("apps.subscriptions.services.SubscriptionService.downgrade_to_free")
    def test_does_not_downgrade_already_free(self, mock_downgrade):
        """Should not downgrade already free subscriptions."""
        user = MasterUserFactory()
        free_plan = FreeMasterPlanFactory()

        sub = ExpiredSubscriptionFactory(
            user=user,
            plan=free_plan
        )

        downgrade_to_free()

        mock_downgrade.assert_not_called()


@pytest.mark.django_db
class TestResetMonthlyUsage:
    """Tests for reset_monthly_usage task."""

    def test_resets_usage_for_active_subscriptions(self):
        """Should reset monthly usage counters."""
        user = MasterUserFactory()
        plan = ProMasterPlanFactory()

        sub = ActiveSubscriptionFactory(
            user=user,
            plan=plan,
            appointments_this_month=50,
            last_usage_reset=None
        )

        result = reset_monthly_usage()

        sub.refresh_from_db()
        assert sub.appointments_this_month == 0
        assert sub.last_usage_reset == timezone.now().date()
        assert "1" in result

    def test_does_not_reset_if_already_reset_today(self):
        """Should not reset if already reset today."""
        user = MasterUserFactory()
        plan = ProMasterPlanFactory()

        today = timezone.now().date()
        sub = ActiveSubscriptionFactory(
            user=user,
            plan=plan,
            appointments_this_month=50,
            last_usage_reset=today
        )

        result = reset_monthly_usage()

        sub.refresh_from_db()
        assert sub.appointments_this_month == 50
        assert "0" in result
