"""
URL routes for subscription management.
"""

from django.urls import path

from .views import (
    CancelSubscriptionView,
    ChangePlanView,
    CheckLimitView,
    CurrentSubscriptionView,
    ReactivateSubscriptionView,
    ReferralListView,
    ReferralStatsView,
    SubscribeView,
    SubscriptionPaymentsView,
    SubscriptionPlanListView,
    SubscriptionUsageView,
    SubscriptionWebhookView,
    TestConfirmPaymentView,
)

urlpatterns = [
    # Plans
    path("plans/", SubscriptionPlanListView.as_view(), name="subscription-plans"),

    # Current subscription
    path("current/", CurrentSubscriptionView.as_view(), name="subscription-current"),
    path("usage/", SubscriptionUsageView.as_view(), name="subscription-usage"),

    # Subscription actions
    path("subscribe/", SubscribeView.as_view(), name="subscription-subscribe"),
    path("cancel/", CancelSubscriptionView.as_view(), name="subscription-cancel"),
    path("reactivate/", ReactivateSubscriptionView.as_view(), name="subscription-reactivate"),
    path("change-plan/", ChangePlanView.as_view(), name="subscription-change-plan"),

    # Payments
    path("payments/", SubscriptionPaymentsView.as_view(), name="subscription-payments"),

    # Limits
    path("check-limit/<str:limit_type>/", CheckLimitView.as_view(), name="subscription-check-limit"),

    # Referral program
    path("referrals/", ReferralListView.as_view(), name="referral-list"),
    path("referrals/stats/", ReferralStatsView.as_view(), name="referral-stats"),

    # Webhooks
    path("webhook/", SubscriptionWebhookView.as_view(), name="subscription-webhook"),
    path("test-confirm/", TestConfirmPaymentView.as_view(), name="subscription-test-confirm"),
]
