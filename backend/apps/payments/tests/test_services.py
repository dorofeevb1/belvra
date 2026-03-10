"""
Tests for payment webhook and related functionality.
"""

import json
import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.appointments.models import Appointment
from apps.payments.models import Payment, PayoutDestination, Wallet, Withdrawal
from apps.payments.services import PaymentService, WithdrawalService, YooKassaService
from apps.users.models import MasterProfile


User = get_user_model()


class WebhookTestCase(APITestCase):
    """Test cases for YooKassa webhook."""

    def setUp(self):
        """Set up test data."""
        # Create users
        self.client_user = User.objects.create_user(
            email="client@test.com",
            password="testpass123",
            first_name="Test",
            last_name="Client"
        )
        self.master_user = User.objects.create_user(
            email="master@test.com",
            password="testpass123",
            first_name="Test",
            last_name="Master",
            role=User.Role.MASTER
        )

        # MasterProfile is created automatically by signal
        self.master = self.master_user.master_profile

        # Wallet is created automatically by signal, get it
        self.wallet = self.master.wallet

        # Create test payment
        self.payment = Payment.objects.create(
            client=self.client_user,
            master=self.master,
            payment_type=Payment.PaymentType.FULL_PAYMENT,
            amount=Decimal("1000.00"),
            status=Payment.PaymentStatus.PENDING,
            external_payment_id="test_payment_123"
        )

        self.webhook_url = reverse("yookassa-webhook")
        self.api_client = APIClient()

    def test_webhook_payment_succeeded(self):
        """Test handling of payment.succeeded webhook."""
        payload = {
            "type": "notification",
            "event": "payment.succeeded",
            "object": {
                "id": "test_payment_123",
                "status": "succeeded",
                "amount": {
                    "value": "1000.00",
                    "currency": "RUB"
                },
                "payment_method": {
                    "type": "bank_card",
                    "id": "pm_123"
                },
                "metadata": {
                    "payment_id": str(self.payment.id)
                }
            }
        }

        response = self.api_client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh payment from database
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.PaymentStatus.SUCCEEDED)
        self.assertIsNotNone(self.payment.paid_at)

        # Check wallet was updated
        self.wallet.refresh_from_db()
        self.assertGreater(self.wallet.pending_balance, Decimal("0.00"))

    def test_webhook_payment_canceled(self):
        """Test handling of payment.canceled webhook."""
        payload = {
            "type": "notification",
            "event": "payment.canceled",
            "object": {
                "id": "test_payment_123",
                "status": "canceled",
                "metadata": {
                    "payment_id": str(self.payment.id)
                },
                "cancellation_details": {
                    "party": "merchant",
                    "reason": "Test cancellation"
                }
            }
        }

        response = self.api_client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh payment from database
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.PaymentStatus.CANCELLED)

    def test_webhook_invalid_event(self):
        """Test webhook rejects invalid events."""
        payload = {
            "type": "notification",
            "event": "invalid.event",
            "object": {}
        }

        response = self.api_client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_webhook_invalid_type(self):
        """Test webhook rejects invalid notification type."""
        payload = {
            "type": "invalid_type",
            "event": "payment.succeeded",
            "object": {}
        }

        response = self.api_client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_webhook_missing_payment_id(self):
        """Test webhook handles missing payment_id gracefully."""
        payload = {
            "type": "notification",
            "event": "payment.succeeded",
            "object": {
                "id": "unknown_payment",
                "status": "succeeded",
                "metadata": {}  # No payment_id
            }
        }

        response = self.api_client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type="application/json"
        )

        # Should return 200 but not process
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_webhook_refund_succeeded(self):
        """Test handling of refund.succeeded webhook."""
        # First make payment succeeded
        self.payment.status = Payment.PaymentStatus.SUCCEEDED
        self.payment.paid_at = "2024-01-01T00:00:00Z"
        self.payment.save()

        payload = {
            "type": "notification",
            "event": "refund.succeeded",
            "object": {
                "id": "refund_123",
                "status": "succeeded",
                "payment_id": "test_payment_123",
                "amount": {
                    "value": "500.00",
                    "currency": "RUB"
                }
            }
        }

        response = self.api_client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh payment
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.refunded_amount, Decimal("500.00"))
        self.assertEqual(self.payment.status, Payment.PaymentStatus.PARTIALLY_REFUNDED)


class PaymentServiceTestCase(TestCase):
    """Test cases for PaymentService."""

    def setUp(self):
        """Set up test data."""
        self.client_user = User.objects.create_user(
            email="client@test.com",
            password="testpass123",
            first_name="Test",
            last_name="Client"
        )

        master_user = User.objects.create_user(
            email="master@test.com",
            password="testpass123",
            role=User.Role.MASTER
        )
        # MasterProfile is created automatically by signal
        self.master = master_user.master_profile
        # Wallet is created automatically by signal
        self.wallet = self.master.wallet

        self.payment = Payment.objects.create(
            client=self.client_user,
            master=self.master,
            payment_type=Payment.PaymentType.FULL_PAYMENT,
            amount=Decimal("1000.00"),
            status=Payment.PaymentStatus.PENDING
        )

    def test_process_successful_payment(self):
        """Test processing a successful payment."""
        service = PaymentService()
        service.process_successful_payment(self.payment, "bank_card")

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.PaymentStatus.SUCCEEDED)
        self.assertEqual(self.payment.payment_method, "bank_card")
        self.assertIsNotNone(self.payment.paid_at)
        self.assertIsNotNone(self.payment.available_at)

        self.wallet.refresh_from_db()
        self.assertGreater(self.wallet.pending_balance, Decimal("0.00"))
        self.assertGreater(self.wallet.total_earned, Decimal("0.00"))

    def test_release_held_funds(self):
        """Test releasing held funds."""
        # First process payment
        service = PaymentService()
        service.process_successful_payment(self.payment, "bank_card")

        self.wallet.refresh_from_db()
        pending_before = self.wallet.pending_balance
        available_before = self.wallet.available_balance

        # Set available_at to past
        from django.utils import timezone
        self.payment.available_at = timezone.now()
        self.payment.save()

        # Release funds
        service.release_held_funds(self.payment)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.pending_balance, Decimal("0.00"))
        self.assertGreater(self.wallet.available_balance, available_before)


class WithdrawalServiceTestCase(TestCase):
    """Test cases for WithdrawalService."""

    def setUp(self):
        """Set up test data."""
        master_user = User.objects.create_user(
            email="master@test.com",
            password="testpass123",
            role=User.Role.MASTER
        )
        # MasterProfile is created automatically by signal
        self.master = master_user.master_profile
        # Wallet is created automatically by signal, update its balance
        self.wallet = self.master.wallet
        self.wallet.available_balance = Decimal("5000.00")
        self.wallet.save()

        self.destination = PayoutDestination.objects.create(
            master=self.master,
            destination_type=PayoutDestination.DestinationType.CARD,
            card_last_four="1234",
            card_type="Visa",
            is_default=True
        )

    def test_create_withdrawal(self):
        """Test creating a withdrawal request."""
        service = WithdrawalService()
        withdrawal = service.create_withdrawal(
            wallet=self.wallet,
            amount=Decimal("1000.00"),
            method="card",
            destination=self.destination
        )

        self.assertEqual(withdrawal.amount, Decimal("1000.00"))
        self.assertEqual(withdrawal.status, Withdrawal.WithdrawalStatus.PENDING)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.available_balance, Decimal("4000.00"))
        self.assertEqual(self.wallet.hold_balance, Decimal("1000.00"))

    def test_create_withdrawal_insufficient_balance(self):
        """Test withdrawal with insufficient balance."""
        service = WithdrawalService()

        with self.assertRaises(ValueError) as ctx:
            service.create_withdrawal(
                wallet=self.wallet,
                amount=Decimal("10000.00"),  # More than available
                method="card",
                destination=self.destination
            )

        self.assertIn("Недостаточно средств", str(ctx.exception))

    def test_create_withdrawal_below_minimum(self):
        """Test withdrawal below minimum amount."""
        service = WithdrawalService()

        with self.assertRaises(ValueError) as ctx:
            service.create_withdrawal(
                wallet=self.wallet,
                amount=Decimal("10.00"),  # Below minimum
                method="card",
                destination=self.destination
            )

        self.assertIn("Минимальная сумма", str(ctx.exception))

    def test_reject_withdrawal(self):
        """Test rejecting a withdrawal."""
        service = WithdrawalService()
        withdrawal = service.create_withdrawal(
            wallet=self.wallet,
            amount=Decimal("1000.00"),
            method="card",
            destination=self.destination
        )

        service.reject_withdrawal(withdrawal, "Test rejection")

        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.status, Withdrawal.WithdrawalStatus.REJECTED)
        self.assertEqual(withdrawal.rejection_reason, "Test rejection")

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.available_balance, Decimal("5000.00"))
        self.assertEqual(self.wallet.hold_balance, Decimal("0.00"))

    def test_complete_withdrawal(self):
        """Test completing a withdrawal."""
        service = WithdrawalService()
        withdrawal = service.create_withdrawal(
            wallet=self.wallet,
            amount=Decimal("1000.00"),
            method="card",
            destination=self.destination
        )

        service.complete_withdrawal(withdrawal)

        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.status, Withdrawal.WithdrawalStatus.COMPLETED)
        self.assertIsNotNone(withdrawal.completed_at)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.hold_balance, Decimal("0.00"))
        self.assertGreater(self.wallet.total_withdrawn, Decimal("0.00"))


class CommissionCalculationTestCase(TestCase):
    """Test cases for commission calculation."""

    def test_payment_commission_calculation(self):
        """Test that commission is calculated correctly."""
        master_user = User.objects.create_user(
            email="master@test.com",
            password="testpass123",
            role=User.Role.MASTER
        )
        # MasterProfile is created automatically by signal
        master = master_user.master_profile

        client_user = User.objects.create_user(
            email="client@test.com",
            password="testpass123"
        )

        payment = Payment.objects.create(
            client=client_user,
            master=master,
            amount=Decimal("1000.00"),
            payment_type=Payment.PaymentType.FULL_PAYMENT
        )

        # Default commission is 5% platform + ~2% provider = ~7%
        self.assertGreater(payment.commission, Decimal("0.00"))
        # net_amount should be amount minus commission
        self.assertLess(payment.net_amount, payment.amount)
        self.assertGreater(payment.net_amount, Decimal("0.00"))

    def test_withdrawal_fee_calculation(self):
        """Test that withdrawal fee is calculated correctly."""
        master_user = User.objects.create_user(
            email="master2@test.com",
            password="testpass123",
            role=User.Role.MASTER
        )
        # MasterProfile is created automatically by signal
        master = master_user.master_profile
        # Wallet is created automatically by signal
        wallet = master.wallet
        wallet.available_balance = Decimal("5000.00")
        wallet.save()

        withdrawal = Withdrawal.objects.create(
            wallet=wallet,
            amount=Decimal("1000.00"),
            method=Withdrawal.WithdrawalMethod.CARD
        )

        # Fee should be calculated
        self.assertGreaterEqual(withdrawal.fee, Decimal("0.00"))
        # net_amount should be amount minus fee
        self.assertLessEqual(withdrawal.net_amount, withdrawal.amount)
