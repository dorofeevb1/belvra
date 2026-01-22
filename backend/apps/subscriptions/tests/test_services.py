"""
Tests for subscription services.
"""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from apps.subscriptions.models import Subscription, SubscriptionPayment, SubscriptionPlan
from apps.subscriptions.services import SubscriptionService
from apps.users.tests.factories import MasterUserFactory, UserFactory

from .factories import (
    ActiveSubscriptionFactory,
    ExpiredSubscriptionFactory,
    FreeMasterPlanFactory,
    ProMasterPlanFactory,
    SubscriptionFactory,
    SubscriptionPaymentFactory,
)


@pytest.mark.django_db
class TestSubscriptionService:
    """Tests for SubscriptionService."""

    def test_get_or_create_free_subscription_creates_new(self):
        """Should create free subscription for user without one."""
        user = MasterUserFactory()
        FreeMasterPlanFactory()  # Ensure free plan exists

        service = SubscriptionService()
        subscription = service.get_or_create_free_subscription(user)

        assert subscription is not None
        assert subscription.user == user
        assert subscription.plan.is_free is True
        assert subscription.status == Subscription.Status.ACTIVE

    def test_get_or_create_free_subscription_returns_existing(self):
        """Should return existing subscription."""
        user = MasterUserFactory()
        existing = ActiveSubscriptionFactory(user=user)

        service = SubscriptionService()
        subscription = service.get_or_create_free_subscription(user)

        assert subscription.id == existing.id

    def test_subscribe_to_free_plan(self):
        """Subscribing to free plan should activate immediately."""
        user = MasterUserFactory()
        plan = FreeMasterPlanFactory()

        service = SubscriptionService()
        result = service.subscribe(
            user=user,
            plan=plan,
            return_url="http://localhost/callback"
        )

        assert result["status"] == "active"
        assert result["payment_url"] is None

        subscription = Subscription.objects.get(user=user)
        assert subscription.status == Subscription.Status.ACTIVE

    def test_subscribe_to_pro_plan_creates_payment(self):
        """Subscribing to pro plan should create payment."""
        user = MasterUserFactory()
        plan = ProMasterPlanFactory()

        service = SubscriptionService()
        result = service.subscribe(
            user=user,
            plan=plan,
            return_url="http://localhost/callback"
        )

        assert result["status"] == "pending"
        assert result["payment_url"] is not None

        subscription = Subscription.objects.get(user=user)
        assert subscription.status == Subscription.Status.PENDING

        payment = SubscriptionPayment.objects.get(subscription=subscription)
        assert payment.amount == plan.price
        assert payment.status == SubscriptionPayment.Status.PENDING

    def test_subscribe_already_subscribed(self):
        """Should return already_subscribed if on same active plan."""
        user = MasterUserFactory()
        plan = ProMasterPlanFactory()
        ActiveSubscriptionFactory(user=user, plan=plan)

        service = SubscriptionService()
        result = service.subscribe(
            user=user,
            plan=plan,
            return_url="http://localhost/callback"
        )

        assert result["status"] == "already_subscribed"

    def test_process_successful_payment(self):
        """Should activate subscription after successful payment."""
        user = MasterUserFactory()
        plan = ProMasterPlanFactory()

        subscription = SubscriptionFactory(
            user=user,
            plan=plan,
            status=Subscription.Status.PENDING
        )
        payment = SubscriptionPaymentFactory(
            subscription=subscription,
            status=SubscriptionPayment.Status.PENDING
        )

        service = SubscriptionService()
        service.process_successful_payment(payment, "test_payment_method_id")

        payment.refresh_from_db()
        subscription.refresh_from_db()

        assert payment.status == SubscriptionPayment.Status.SUCCEEDED
        assert payment.paid_at is not None
        assert subscription.status == Subscription.Status.ACTIVE
        assert subscription.current_period_start is not None
        assert subscription.current_period_end is not None
        assert subscription.yookassa_payment_method_id == "test_payment_method_id"

    def test_cancel_subscription_at_period_end(self):
        """Cancel at period end should set flag but keep active."""
        user = MasterUserFactory()
        plan = ProMasterPlanFactory()
        subscription = ActiveSubscriptionFactory(user=user, plan=plan)

        service = SubscriptionService()
        result = service.cancel_subscription(subscription, immediately=False)

        assert result.cancel_at_period_end is True
        assert result.status == Subscription.Status.ACTIVE
        assert result.auto_renew is False

    def test_cancel_subscription_immediately(self):
        """Cancel immediately should set status to cancelled."""
        user = MasterUserFactory()
        plan = ProMasterPlanFactory()
        subscription = ActiveSubscriptionFactory(user=user, plan=plan)

        service = SubscriptionService()
        result = service.cancel_subscription(subscription, immediately=True)

        assert result.status == Subscription.Status.CANCELLED
        assert result.cancelled_at is not None

    def test_reactivate_subscription(self):
        """Should reactivate a subscription marked for cancellation."""
        user = MasterUserFactory()
        plan = ProMasterPlanFactory()
        subscription = ActiveSubscriptionFactory(
            user=user,
            plan=plan,
            cancel_at_period_end=True,
            auto_renew=False
        )

        service = SubscriptionService()
        result = service.reactivate_subscription(subscription)

        assert result.cancel_at_period_end is False
        assert result.auto_renew is True

    def test_reactivate_already_cancelled_raises_error(self):
        """Should raise error for fully cancelled subscription."""
        user = MasterUserFactory()
        plan = ProMasterPlanFactory()
        subscription = SubscriptionFactory(
            user=user,
            plan=plan,
            status=Subscription.Status.CANCELLED
        )

        service = SubscriptionService()
        with pytest.raises(ValueError):
            service.reactivate_subscription(subscription)

    def test_change_plan_to_free_immediately(self):
        """Downgrading to free immediately should update plan."""
        user = MasterUserFactory()
        pro_plan = ProMasterPlanFactory()
        free_plan = FreeMasterPlanFactory()
        subscription = ActiveSubscriptionFactory(user=user, plan=pro_plan)

        service = SubscriptionService()
        result = service.change_plan(subscription, free_plan, immediately=True)

        subscription.refresh_from_db()
        assert result["status"] == "downgraded"
        assert subscription.plan == free_plan

    def test_change_plan_to_free_at_period_end(self):
        """Downgrading to free at period end should set cancel flag."""
        user = MasterUserFactory()
        pro_plan = ProMasterPlanFactory()
        free_plan = FreeMasterPlanFactory()
        subscription = ActiveSubscriptionFactory(user=user, plan=pro_plan)

        service = SubscriptionService()
        result = service.change_plan(subscription, free_plan, immediately=False)

        subscription.refresh_from_db()
        assert result["status"] == "downgraded"
        assert subscription.cancel_at_period_end is True

    def test_change_plan_upgrade_requires_payment(self):
        """Upgrading should require payment."""
        user = MasterUserFactory()
        free_plan = FreeMasterPlanFactory()
        pro_plan = ProMasterPlanFactory()
        subscription = ActiveSubscriptionFactory(user=user, plan=free_plan)

        service = SubscriptionService()
        result = service.change_plan(subscription, pro_plan)

        assert result["status"] == "payment_required"

    def test_get_usage_stats(self):
        """Should return correct usage statistics."""
        user = MasterUserFactory()
        plan = FreeMasterPlanFactory(
            max_appointments_per_month=10,
            max_services_count=5,
            max_portfolio_items=5
        )
        subscription = ActiveSubscriptionFactory(
            user=user,
            plan=plan,
            appointments_this_month=3
        )

        service = SubscriptionService()
        stats = service.get_usage_stats(subscription)

        assert stats["appointments_used"] == 3
        assert stats["appointments_limit"] == 10
        assert stats["appointments_remaining"] == 7
        assert stats["plan_tier"] == "free"

    def test_check_limit_allowed(self):
        """Should return allowed when under limit."""
        user = MasterUserFactory()
        plan = FreeMasterPlanFactory(max_appointments_per_month=10)
        subscription = ActiveSubscriptionFactory(
            user=user,
            plan=plan,
            appointments_this_month=5
        )

        service = SubscriptionService()
        result = service.check_limit(subscription, "appointments")

        assert result["allowed"] is True
        assert result["current"] == 5
        assert result["limit"] == 10
        assert result["remaining"] == 5

    def test_check_limit_reached(self):
        """Should return not allowed when at limit."""
        user = MasterUserFactory()
        plan = FreeMasterPlanFactory(max_appointments_per_month=10)
        subscription = ActiveSubscriptionFactory(
            user=user,
            plan=plan,
            appointments_this_month=10
        )

        service = SubscriptionService()
        result = service.check_limit(subscription, "appointments")

        assert result["allowed"] is False
        assert result["message"] is not None

    def test_check_limit_unlimited(self):
        """Should handle unlimited limits."""
        user = MasterUserFactory()
        plan = ProMasterPlanFactory(max_appointments_per_month=0)
        subscription = ActiveSubscriptionFactory(
            user=user,
            plan=plan,
            appointments_this_month=1000
        )

        service = SubscriptionService()
        result = service.check_limit(subscription, "appointments")

        assert result["allowed"] is True
        assert result["limit"] == -1  # Unlimited indicator

    def test_expire_subscription(self):
        """Should mark subscription as expired."""
        user = MasterUserFactory()
        plan = ProMasterPlanFactory()
        subscription = ActiveSubscriptionFactory(
            user=user,
            plan=plan,
            current_period_end=timezone.now() - timedelta(days=1)
        )

        service = SubscriptionService()
        service.expire_subscription(subscription)

        subscription.refresh_from_db()
        assert subscription.status == Subscription.Status.EXPIRED

    def test_downgrade_to_free(self):
        """Should downgrade to free plan."""
        user = MasterUserFactory()
        pro_plan = ProMasterPlanFactory()
        free_plan = FreeMasterPlanFactory()

        subscription = ExpiredSubscriptionFactory(user=user, plan=pro_plan)

        service = SubscriptionService()
        service.downgrade_to_free(subscription)

        subscription.refresh_from_db()
        assert subscription.plan == free_plan
        assert subscription.status == Subscription.Status.ACTIVE
        assert subscription.current_period_end is None


@pytest.mark.django_db
class TestSubscriptionServiceRenewal:
    """Tests for subscription renewal functionality."""

    def test_renew_subscription_without_payment_method(self):
        """Should return None if no payment method saved."""
        user = MasterUserFactory()
        plan = ProMasterPlanFactory()
        subscription = ActiveSubscriptionFactory(
            user=user,
            plan=plan,
            yookassa_payment_method_id=""
        )

        service = SubscriptionService()
        result = service.renew_subscription(subscription)

        assert result is None

    def test_renew_subscription_auto_renew_off(self):
        """Should return None if auto_renew is off."""
        user = MasterUserFactory()
        plan = ProMasterPlanFactory()
        subscription = ActiveSubscriptionFactory(
            user=user,
            plan=plan,
            auto_renew=False,
            yookassa_payment_method_id="pm_123"
        )

        service = SubscriptionService()
        result = service.renew_subscription(subscription)

        assert result is None

    def test_renew_subscription_free_plan(self):
        """Should return None for free plan."""
        user = MasterUserFactory()
        plan = FreeMasterPlanFactory()
        subscription = ActiveSubscriptionFactory(
            user=user,
            plan=plan,
            yookassa_payment_method_id="pm_123"
        )

        service = SubscriptionService()
        result = service.renew_subscription(subscription)

        assert result is None
