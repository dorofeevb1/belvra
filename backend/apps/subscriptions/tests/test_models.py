"""
Tests for subscription models.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.subscriptions.models import Subscription, SubscriptionPayment, SubscriptionPlan

from .factories import (
    ActiveSubscriptionFactory,
    ExpiredSubscriptionFactory,
    FreeMasterPlanFactory,
    ProMasterPlanFactory,
    SubscriptionFactory,
    SubscriptionPaymentFactory,
    SubscriptionPlanFactory,
)


@pytest.mark.django_db
class TestSubscriptionPlan:
    """Tests for SubscriptionPlan model."""

    def test_create_plan(self):
        """Test creating a subscription plan."""
        plan = SubscriptionPlanFactory(
            name="Test Plan",
            tier=SubscriptionPlan.Tier.PRO,
            price=Decimal("999.00")
        )
        assert plan.name == "Test Plan"
        assert plan.tier == SubscriptionPlan.Tier.PRO
        assert plan.price == Decimal("999.00")

    def test_is_free_property(self):
        """Test is_free property."""
        free_plan = FreeMasterPlanFactory()
        pro_plan = ProMasterPlanFactory()

        assert free_plan.is_free is True
        assert pro_plan.is_free is False

    def test_is_pro_property(self):
        """Test is_pro property."""
        free_plan = FreeMasterPlanFactory()
        pro_plan = ProMasterPlanFactory()

        assert free_plan.is_pro is False
        assert pro_plan.is_pro is True

    def test_unique_together_constraint(self):
        """Test unique_together for tier, user_type, period."""
        FreeMasterPlanFactory(
            tier=SubscriptionPlan.Tier.FREE,
            user_type=SubscriptionPlan.UserType.MASTER,
            period=SubscriptionPlan.Period.MONTHLY
        )

        # Creating another plan with same tier/user_type/period should fail
        with pytest.raises(Exception):
            FreeMasterPlanFactory(
                tier=SubscriptionPlan.Tier.FREE,
                user_type=SubscriptionPlan.UserType.MASTER,
                period=SubscriptionPlan.Period.MONTHLY
            )


@pytest.mark.django_db
class TestSubscription:
    """Tests for Subscription model."""

    def test_create_subscription(self):
        """Test creating a subscription."""
        subscription = SubscriptionFactory()
        assert subscription.id is not None
        assert subscription.user is not None
        assert subscription.plan is not None

    def test_is_active_property_active_status(self):
        """Test is_active property with active status."""
        subscription = ActiveSubscriptionFactory()
        assert subscription.is_active is True

    def test_is_active_property_expired_end_date(self):
        """Test is_active property with expired end date."""
        subscription = ActiveSubscriptionFactory(
            current_period_end=timezone.now() - timedelta(days=1)
        )
        assert subscription.is_active is False

    def test_is_active_property_wrong_status(self):
        """Test is_active property with non-active status."""
        subscription = ExpiredSubscriptionFactory()
        assert subscription.is_active is False

    def test_days_until_expiry(self):
        """Test days_until_expiry property."""
        subscription = ActiveSubscriptionFactory(
            current_period_end=timezone.now() + timedelta(days=10)
        )
        assert 9 <= subscription.days_until_expiry <= 10

    def test_days_until_expiry_expired(self):
        """Test days_until_expiry for expired subscription."""
        subscription = ExpiredSubscriptionFactory(
            current_period_end=timezone.now() - timedelta(days=5)
        )
        assert subscription.days_until_expiry == 0

    def test_days_until_expiry_none(self):
        """Test days_until_expiry when no end date (free plan)."""
        subscription = ActiveSubscriptionFactory(
            current_period_end=None
        )
        assert subscription.days_until_expiry is None

    def test_reset_monthly_usage(self):
        """Test reset_monthly_usage method."""
        subscription = ActiveSubscriptionFactory(
            appointments_this_month=50
        )
        subscription.reset_monthly_usage()

        subscription.refresh_from_db()
        assert subscription.appointments_this_month == 0
        assert subscription.last_usage_reset == timezone.now().date()

    def test_can_create_appointment_within_limit(self):
        """Test can_create_appointment within limit."""
        plan = FreeMasterPlanFactory(max_appointments_per_month=10)
        subscription = ActiveSubscriptionFactory(
            plan=plan,
            appointments_this_month=5
        )
        assert subscription.can_create_appointment() is True

    def test_can_create_appointment_at_limit(self):
        """Test can_create_appointment at limit."""
        plan = FreeMasterPlanFactory(max_appointments_per_month=10)
        subscription = ActiveSubscriptionFactory(
            plan=plan,
            appointments_this_month=10
        )
        assert subscription.can_create_appointment() is False

    def test_can_create_appointment_unlimited(self):
        """Test can_create_appointment with unlimited plan."""
        plan = ProMasterPlanFactory(max_appointments_per_month=0)  # 0 = unlimited
        subscription = ActiveSubscriptionFactory(
            plan=plan,
            appointments_this_month=1000
        )
        assert subscription.can_create_appointment() is True

    def test_can_add_service_within_limit(self):
        """Test can_add_service within limit."""
        plan = FreeMasterPlanFactory(max_services_count=5)
        subscription = ActiveSubscriptionFactory(plan=plan)
        assert subscription.can_add_service(current_count=3) is True

    def test_can_add_service_at_limit(self):
        """Test can_add_service at limit."""
        plan = FreeMasterPlanFactory(max_services_count=5)
        subscription = ActiveSubscriptionFactory(plan=plan)
        assert subscription.can_add_service(current_count=5) is False

    def test_can_add_portfolio_item_unlimited(self):
        """Test can_add_portfolio_item with unlimited plan."""
        plan = ProMasterPlanFactory(max_portfolio_items=0)
        subscription = ActiveSubscriptionFactory(plan=plan)
        assert subscription.can_add_portfolio_item(current_count=100) is True


@pytest.mark.django_db
class TestSubscriptionPayment:
    """Tests for SubscriptionPayment model."""

    def test_create_payment(self):
        """Test creating a payment."""
        payment = SubscriptionPaymentFactory(
            amount=Decimal("999.00"),
            status=SubscriptionPayment.Status.PENDING
        )
        assert payment.id is not None
        assert payment.amount == Decimal("999.00")
        assert payment.status == SubscriptionPayment.Status.PENDING

    def test_payment_relationship(self):
        """Test payment-subscription relationship."""
        subscription = SubscriptionFactory()
        payment = SubscriptionPaymentFactory(subscription=subscription)

        assert payment.subscription == subscription
        assert payment in subscription.payments.all()

    def test_payment_str(self):
        """Test payment string representation."""
        payment = SubscriptionPaymentFactory()
        str_repr = str(payment)

        assert str(payment.id) in str_repr
        assert payment.subscription.user.email in str_repr
