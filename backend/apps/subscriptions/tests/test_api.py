"""
Tests for subscription API endpoints.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.subscriptions.models import Subscription, SubscriptionPayment, SubscriptionPlan
from apps.users.tests.factories import MasterUserFactory, UserFactory

from .factories import (
    ActiveSubscriptionFactory,
    FreeMasterPlanFactory,
    FreeClientPlanFactory,
    ProMasterPlanFactory,
    SubscriptionFactory,
    SubscriptionPaymentFactory,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory(password="testpass123")


@pytest.fixture
def master_user(db):
    return MasterUserFactory(password="testpass123")


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def master_client(api_client, master_user):
    api_client.force_authenticate(user=master_user)
    return api_client


@pytest.mark.django_db
class TestSubscriptionPlanList:
    """Tests for listing subscription plans."""

    def test_list_plans_unauthenticated(self, api_client):
        """Plans list should be accessible without authentication."""
        FreeMasterPlanFactory()
        ProMasterPlanFactory()

        url = reverse("subscription-plans")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Handle both paginated and non-paginated responses
        results = response.data.get("results", response.data)
        assert len(results) >= 2

    def test_filter_by_user_type(self, api_client):
        """Plans can be filtered by user_type."""
        FreeMasterPlanFactory()
        FreeClientPlanFactory()

        url = reverse("subscription-plans")
        response = api_client.get(url, {"user_type": "master"})

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)

        for plan in results:
            assert plan["user_type"] == "master"

    def test_only_active_plans(self, api_client):
        """Only active plans should be returned."""
        active_plan = FreeMasterPlanFactory(is_active=True)
        inactive_plan = FreeMasterPlanFactory(
            is_active=False,
            tier=SubscriptionPlan.Tier.PRO  # Different to avoid unique constraint
        )

        url = reverse("subscription-plans")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        plan_ids = [p["id"] for p in results]

        assert str(active_plan.id) in plan_ids
        assert str(inactive_plan.id) not in plan_ids


@pytest.mark.django_db
class TestCurrentSubscription:
    """Tests for getting current subscription."""

    def test_get_current_subscription(self, authenticated_client, user):
        """Should return current subscription."""
        plan = FreeClientPlanFactory()
        subscription = ActiveSubscriptionFactory(user=user, plan=plan)

        url = reverse("subscription-current")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(subscription.id)
        assert response.data["status"] == "active"

    def test_creates_free_subscription_if_none(self, master_client, master_user):
        """Should create free subscription if user doesn't have one."""
        # Create free plan first
        FreeMasterPlanFactory()

        url = reverse("subscription-current")
        response = master_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "active"
        assert Subscription.objects.filter(user=master_user).exists()

    def test_requires_authentication(self, api_client):
        """Should require authentication."""
        url = reverse("subscription-current")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestSubscriptionUsage:
    """Tests for subscription usage stats."""

    def test_get_usage_stats(self, master_client, master_user):
        """Should return usage statistics."""
        plan = FreeMasterPlanFactory(
            max_appointments_per_month=10,
            max_services_count=5,
            max_portfolio_items=5
        )
        ActiveSubscriptionFactory(
            user=master_user,
            plan=plan,
            appointments_this_month=3
        )

        url = reverse("subscription-usage")
        response = master_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["appointments_used"] == 3
        assert response.data["appointments_limit"] == 10
        assert response.data["appointments_remaining"] == 7


@pytest.mark.django_db
class TestSubscribe:
    """Tests for subscribing to a plan."""

    def test_subscribe_to_free_plan(self, master_client, master_user):
        """Subscribing to free plan should not require payment."""
        plan = FreeMasterPlanFactory()

        url = reverse("subscription-subscribe")
        response = master_client.post(url, {
            "plan_id": str(plan.id)
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "active"
        assert response.data["payment_url"] is None

    def test_subscribe_to_pro_plan_returns_payment_url(self, master_client, master_user):
        """Subscribing to pro plan should return payment URL."""
        plan = ProMasterPlanFactory()

        url = reverse("subscription-subscribe")
        response = master_client.post(url, {
            "plan_id": str(plan.id),
            "return_url": "http://localhost:4200/subscription/success"
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "pending"
        assert response.data["payment_url"] is not None

        # Verify subscription and payment were created
        subscription = Subscription.objects.get(user=master_user)
        assert subscription.status == Subscription.Status.PENDING
        assert SubscriptionPayment.objects.filter(subscription=subscription).exists()

    def test_subscribe_plan_not_found(self, authenticated_client):
        """Should return 404 for non-existent plan."""
        url = reverse("subscription-subscribe")
        response = authenticated_client.post(url, {
            "plan_id": "00000000-0000-0000-0000-000000000000"
        })

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_already_subscribed(self, master_client, master_user):
        """Should return already_subscribed if on same plan."""
        plan = ProMasterPlanFactory()
        ActiveSubscriptionFactory(
            user=master_user,
            plan=plan,
            status=Subscription.Status.ACTIVE
        )

        url = reverse("subscription-subscribe")
        response = master_client.post(url, {
            "plan_id": str(plan.id)
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "already_subscribed"


@pytest.mark.django_db
class TestCancelSubscription:
    """Tests for cancelling subscription."""

    def test_cancel_at_period_end(self, master_client, master_user):
        """Cancel at period end should set cancel_at_period_end flag."""
        plan = ProMasterPlanFactory()
        subscription = ActiveSubscriptionFactory(
            user=master_user,
            plan=plan
        )

        url = reverse("subscription-cancel")
        response = master_client.post(url, {
            "immediately": False
        })

        assert response.status_code == status.HTTP_200_OK

        subscription.refresh_from_db()
        assert subscription.cancel_at_period_end is True
        assert subscription.status == Subscription.Status.ACTIVE

    def test_cancel_immediately(self, master_client, master_user):
        """Cancel immediately should set status to cancelled."""
        plan = ProMasterPlanFactory()
        subscription = ActiveSubscriptionFactory(
            user=master_user,
            plan=plan
        )

        url = reverse("subscription-cancel")
        response = master_client.post(url, {
            "immediately": True
        })

        assert response.status_code == status.HTTP_200_OK

        subscription.refresh_from_db()
        assert subscription.status == Subscription.Status.CANCELLED
        assert subscription.cancelled_at is not None

    def test_cannot_cancel_free_plan(self, master_client, master_user):
        """Cannot cancel free plan."""
        plan = FreeMasterPlanFactory()
        ActiveSubscriptionFactory(
            user=master_user,
            plan=plan
        )

        url = reverse("subscription-cancel")
        response = master_client.post(url, {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestReactivateSubscription:
    """Tests for reactivating subscription."""

    def test_reactivate_cancelled_subscription(self, master_client, master_user):
        """Should reactivate a subscription marked for cancellation."""
        plan = ProMasterPlanFactory()
        subscription = ActiveSubscriptionFactory(
            user=master_user,
            plan=plan,
            cancel_at_period_end=True
        )

        url = reverse("subscription-reactivate")
        response = master_client.post(url)

        assert response.status_code == status.HTTP_200_OK

        subscription.refresh_from_db()
        assert subscription.cancel_at_period_end is False
        assert subscription.auto_renew is True

    def test_reactivate_not_cancelled(self, master_client, master_user):
        """Should return error if subscription is not cancelled."""
        plan = ProMasterPlanFactory()
        ActiveSubscriptionFactory(
            user=master_user,
            plan=plan,
            cancel_at_period_end=False
        )

        url = reverse("subscription-reactivate")
        response = master_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestCheckLimit:
    """Tests for checking subscription limits."""

    def test_check_appointments_limit_allowed(self, master_client, master_user):
        """Should return allowed=True when under limit."""
        plan = FreeMasterPlanFactory(max_appointments_per_month=10)
        ActiveSubscriptionFactory(
            user=master_user,
            plan=plan,
            appointments_this_month=5
        )

        url = reverse("subscription-check-limit", kwargs={"limit_type": "appointments"})
        response = master_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["allowed"] is True
        assert response.data["current"] == 5
        assert response.data["limit"] == 10
        assert response.data["remaining"] == 5

    def test_check_appointments_limit_reached(self, master_client, master_user):
        """Should return allowed=False when at limit."""
        plan = FreeMasterPlanFactory(max_appointments_per_month=10)
        ActiveSubscriptionFactory(
            user=master_user,
            plan=plan,
            appointments_this_month=10
        )

        url = reverse("subscription-check-limit", kwargs={"limit_type": "appointments"})
        response = master_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["allowed"] is False
        assert response.data["message"] is not None

    def test_check_unlimited_limit(self, master_client, master_user):
        """Should return unlimited indicator for pro plans."""
        plan = ProMasterPlanFactory(max_appointments_per_month=0)
        ActiveSubscriptionFactory(
            user=master_user,
            plan=plan,
            appointments_this_month=100
        )

        url = reverse("subscription-check-limit", kwargs={"limit_type": "appointments"})
        response = master_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["allowed"] is True
        assert response.data["limit"] == -1  # -1 indicates unlimited

    def test_check_invalid_limit_type(self, master_client, master_user):
        """Should return error for invalid limit type."""
        plan = FreeMasterPlanFactory()
        ActiveSubscriptionFactory(user=master_user, plan=plan)

        url = reverse("subscription-check-limit", kwargs={"limit_type": "invalid"})
        response = master_client.get(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestSubscriptionPayments:
    """Tests for subscription payment history."""

    def test_list_payments(self, master_client, master_user):
        """Should list payment history."""
        plan = ProMasterPlanFactory()
        subscription = ActiveSubscriptionFactory(
            user=master_user,
            plan=plan
        )
        SubscriptionPaymentFactory(subscription=subscription)
        SubscriptionPaymentFactory(subscription=subscription)

        url = reverse("subscription-payments")
        response = master_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        assert len(results) == 2

    def test_list_payments_only_own(self, authenticated_client, user):
        """Should only list own payments."""
        plan = ProMasterPlanFactory()

        # Own subscription
        own_subscription = ActiveSubscriptionFactory(user=user, plan=plan)
        SubscriptionPaymentFactory(subscription=own_subscription)

        # Other user's subscription
        other_subscription = ActiveSubscriptionFactory(plan=plan)
        SubscriptionPaymentFactory(subscription=other_subscription)

        url = reverse("subscription-payments")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results", response.data)
        assert len(results) == 1


@pytest.mark.django_db
class TestTestConfirmPayment:
    """Tests for test payment confirmation endpoint."""

    def test_confirm_test_payment(self, master_client, master_user):
        """Should confirm test payment."""
        plan = ProMasterPlanFactory()
        subscription = SubscriptionFactory(
            user=master_user,
            plan=plan,
            status=Subscription.Status.PENDING
        )
        payment = SubscriptionPaymentFactory(
            subscription=subscription,
            status=SubscriptionPayment.Status.PENDING,
            external_payment_id="test_abc123"
        )

        url = reverse("subscription-test-confirm")
        response = master_client.post(url, {
            "payment_id": str(payment.id)
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "success"

        payment.refresh_from_db()
        subscription.refresh_from_db()

        assert payment.status == SubscriptionPayment.Status.SUCCEEDED
        assert subscription.status == Subscription.Status.ACTIVE

    def test_cannot_confirm_non_test_payment(self, master_client, master_user):
        """Should reject non-test payments."""
        plan = ProMasterPlanFactory()
        subscription = SubscriptionFactory(
            user=master_user,
            plan=plan,
            status=Subscription.Status.PENDING
        )
        payment = SubscriptionPaymentFactory(
            subscription=subscription,
            external_payment_id="real_payment_id"  # Not a test payment
        )

        url = reverse("subscription-test-confirm")
        response = master_client.post(url, {
            "payment_id": str(payment.id)
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_confirm_others_payment(self, master_client, master_user):
        """Should reject confirming other user's payment."""
        other_user = UserFactory()
        plan = ProMasterPlanFactory()
        subscription = SubscriptionFactory(
            user=other_user,
            plan=plan,
            status=Subscription.Status.PENDING
        )
        payment = SubscriptionPaymentFactory(
            subscription=subscription,
            external_payment_id="test_abc123"
        )

        url = reverse("subscription-test-confirm")
        response = master_client.post(url, {
            "payment_id": str(payment.id)
        })

        assert response.status_code == status.HTTP_403_FORBIDDEN
