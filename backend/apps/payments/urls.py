"""
URL routes for payment API.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.payments.views import (
    ClientPaymentListView,
    MasterPaymentListView,
    PaymentViewSet,
    PayoutDestinationViewSet,
    TransactionListView,
    TransactionSummaryView,
    WalletStatsView,
    WalletView,
    WithdrawalViewSet,
    YooKassaWebhookView,
)

router = DefaultRouter()
router.register(r"payments", PaymentViewSet, basename="payment")
router.register(r"payout-destinations", PayoutDestinationViewSet, basename="payout-destination")
router.register(r"withdrawals", WithdrawalViewSet, basename="withdrawal")

urlpatterns = [
    # Wallet endpoints
    path("wallet/", WalletView.as_view(), name="wallet"),
    path("wallet/stats/", WalletStatsView.as_view(), name="wallet-stats"),

    # Payment history endpoints
    path("my-payments/", ClientPaymentListView.as_view(), name="client-payments"),
    path("received-payments/", MasterPaymentListView.as_view(), name="master-payments"),

    # Transaction endpoints (computed from appointments)
    path("transactions/", TransactionListView.as_view(), name="transactions"),
    path("transactions/summary/", TransactionSummaryView.as_view(), name="transaction-summary"),

    # Webhook endpoint
    path("webhook/yookassa/", YooKassaWebhookView.as_view(), name="yookassa-webhook"),

    # Router URLs
    path("", include(router.urls)),
]
