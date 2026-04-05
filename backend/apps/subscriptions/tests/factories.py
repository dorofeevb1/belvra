"""
Factories for subscription tests.
"""

from datetime import timedelta
from decimal import Decimal

import factory
from django.utils import timezone
from faker import Faker

from apps.subscriptions.models import Subscription, SubscriptionPayment, SubscriptionPlan
from apps.users.tests.factories import MasterUserFactory, UserFactory

fake = Faker("ru_RU")


class SubscriptionPlanFactory(factory.django.DjangoModelFactory):
    """Factory for SubscriptionPlan."""

    class Meta:
        model = SubscriptionPlan

    name = factory.LazyAttribute(lambda _: f"Plan {fake.word()}")
    tier = SubscriptionPlan.Tier.FREE
    user_type = SubscriptionPlan.UserType.MASTER
    period = SubscriptionPlan.Period.MONTHLY
    price = Decimal("0")
    is_active = True
    max_appointments_per_month = 10
    max_services_count = 5
    max_portfolio_items = 5
    commission_percent = Decimal("10.00")
    extended_search = False
    history_months = 3
    client_stats_enabled = False
    max_favorites = 5
    pro_badge = False
    client_notes_enabled = False
    max_pinned_portfolio = 0
    rebooking_reminder_enabled = False


class FreeMasterPlanFactory(SubscriptionPlanFactory):
    """Factory for free master plan."""

    name = "Бесплатный (master)"
    tier = SubscriptionPlan.Tier.FREE
    user_type = SubscriptionPlan.UserType.MASTER
    price = Decimal("0")
    max_appointments_per_month = 10
    max_services_count = 5
    max_portfolio_items = 5
    commission_percent = Decimal("10.00")
    pro_badge = False
    client_notes_enabled = False
    max_pinned_portfolio = 0
    rebooking_reminder_enabled = False
    extended_search = False
    history_months = 3
    client_stats_enabled = False
    max_favorites = 5


class ProMasterPlanFactory(SubscriptionPlanFactory):
    """Factory for pro master plan."""

    name = "Pro (master)"
    tier = SubscriptionPlan.Tier.PRO
    user_type = SubscriptionPlan.UserType.MASTER
    price = Decimal("999.00")
    max_appointments_per_month = 0  # Unlimited
    max_services_count = 0  # Unlimited
    max_portfolio_items = 0  # Unlimited
    commission_percent = Decimal("5.00")
    search_boost_enabled = True
    analytics_level = SubscriptionPlan.AnalyticsLevel.ADVANCED
    ai_assistant_enabled = True
    pro_badge = True
    client_notes_enabled = True
    max_pinned_portfolio = 3
    rebooking_reminder_enabled = True
    extended_search = True
    history_months = 0
    client_stats_enabled = True
    max_favorites = 0


class FreeClientPlanFactory(SubscriptionPlanFactory):
    """Factory for free client plan."""

    name = "Бесплатный (client)"
    tier = SubscriptionPlan.Tier.FREE
    user_type = SubscriptionPlan.UserType.CLIENT
    price = Decimal("0")
    max_appointments_per_month = 0
    max_services_count = 0
    max_portfolio_items = 0
    extended_search = False
    history_months = 3
    client_stats_enabled = False
    max_favorites = 5
    pro_badge = False
    client_notes_enabled = False
    max_pinned_portfolio = 0
    rebooking_reminder_enabled = False


class ProClientPlanFactory(SubscriptionPlanFactory):
    """Factory for pro client plan."""

    name = "Pro (client)"
    tier = SubscriptionPlan.Tier.PRO
    user_type = SubscriptionPlan.UserType.CLIENT
    price = Decimal("299.00")
    priority_booking = True
    cashback_percent = Decimal("5.00")
    discount_percent = Decimal("10.00")
    extended_search = True
    history_months = 0
    client_stats_enabled = True
    max_favorites = 0
    pro_badge = False
    client_notes_enabled = False
    max_pinned_portfolio = 0
    rebooking_reminder_enabled = False


class SubscriptionFactory(factory.django.DjangoModelFactory):
    """Factory for Subscription."""

    class Meta:
        model = Subscription

    user = factory.SubFactory(UserFactory)
    plan = factory.SubFactory(FreeMasterPlanFactory)
    status = Subscription.Status.ACTIVE
    current_period_start = factory.LazyAttribute(lambda _: timezone.now())
    current_period_end = factory.LazyAttribute(lambda _: timezone.now() + timedelta(days=30))
    auto_renew = True


class ActiveSubscriptionFactory(SubscriptionFactory):
    """Factory for active subscription."""

    status = Subscription.Status.ACTIVE


class PendingSubscriptionFactory(SubscriptionFactory):
    """Factory for pending subscription."""

    status = Subscription.Status.PENDING
    current_period_start = None
    current_period_end = None


class ExpiredSubscriptionFactory(SubscriptionFactory):
    """Factory for expired subscription."""

    status = Subscription.Status.EXPIRED
    current_period_end = factory.LazyAttribute(lambda _: timezone.now() - timedelta(days=1))


class SubscriptionPaymentFactory(factory.django.DjangoModelFactory):
    """Factory for SubscriptionPayment."""

    class Meta:
        model = SubscriptionPayment

    subscription = factory.SubFactory(SubscriptionFactory)
    amount = Decimal("999.00")
    currency = "RUB"
    status = SubscriptionPayment.Status.PENDING


class SucceededPaymentFactory(SubscriptionPaymentFactory):
    """Factory for succeeded payment."""

    status = SubscriptionPayment.Status.SUCCEEDED
    paid_at = factory.LazyAttribute(lambda _: timezone.now())
    external_payment_id = factory.LazyAttribute(lambda _: f"test_{fake.uuid4()}")
