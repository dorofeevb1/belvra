"""
Tests for wallet and withdrawal flow.

Covers:
- Wallet creation (auto-created by signal for masters)
- Withdrawal with sufficient balance
- Withdrawal with insufficient balance
- Withdrawal ownership check
- Withdrawal fee calculation
- Withdrawal rejection returns funds
- Withdrawal completion updates totals
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.payments.models import Payment, PayoutDestination, Wallet, Withdrawal
from apps.payments.services import PaymentService, WithdrawalService

User = get_user_model()


class WalletCreationTest(TestCase):
    """Test that wallets are created correctly."""

    def test_wallet_auto_created_for_master(self):
        """Wallet should be auto-created when a master profile is created."""
        master_user = User.objects.create_user(
            email="master_wallet_create@test.com",
            password="testpass123",
            first_name="Master",
            last_name="WalletCreate",
            role=User.Role.MASTER,
        )
        master = master_user.master_profile
        wallet = master.wallet

        self.assertIsNotNone(wallet)
        self.assertEqual(wallet.available_balance, Decimal("0.00"))
        self.assertEqual(wallet.pending_balance, Decimal("0.00"))
        self.assertEqual(wallet.hold_balance, Decimal("0.00"))
        self.assertEqual(wallet.total_earned, Decimal("0.00"))
        self.assertEqual(wallet.total_withdrawn, Decimal("0.00"))

    def test_wallet_total_balance_property(self):
        """total_balance should equal available + pending."""
        master_user = User.objects.create_user(
            email="master_total@test.com",
            password="testpass123",
            role=User.Role.MASTER,
        )
        wallet = master_user.master_profile.wallet
        wallet.available_balance = Decimal("1000.00")
        wallet.pending_balance = Decimal("500.00")
        wallet.save()

        self.assertEqual(wallet.total_balance, Decimal("1500.00"))

    def test_wallet_str(self):
        master_user = User.objects.create_user(
            email="master_str@test.com",
            password="testpass123",
            first_name="John",
            last_name="Doe",
            role=User.Role.MASTER,
        )
        wallet = master_user.master_profile.wallet
        wallet_str = str(wallet)
        self.assertIn("John Doe", wallet_str)


class WithdrawalSufficientBalanceTest(TestCase):
    """Test withdrawal with sufficient balance."""

    def setUp(self):
        self.master_user = User.objects.create_user(
            email="master_withdraw@test.com",
            password="testpass123",
            first_name="Master",
            last_name="Withdraw",
            role=User.Role.MASTER,
        )
        self.master = self.master_user.master_profile
        self.wallet = self.master.wallet
        self.wallet.available_balance = Decimal("5000.00")
        self.wallet.save()

        self.destination = PayoutDestination.objects.create(
            master=self.master,
            destination_type=PayoutDestination.DestinationType.CARD,
            card_last_four="4321",
            card_type="Visa",
            is_default=True,
        )

    def test_create_withdrawal_deducts_from_available(self):
        """Withdrawal should move funds from available to hold."""
        service = WithdrawalService()
        withdrawal = service.create_withdrawal(
            wallet=self.wallet,
            amount=Decimal("1000.00"),
            method="card",
            destination=self.destination,
        )

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.available_balance, Decimal("4000.00"))
        self.assertEqual(self.wallet.hold_balance, Decimal("1000.00"))

    def test_withdrawal_status_is_pending(self):
        service = WithdrawalService()
        withdrawal = service.create_withdrawal(
            wallet=self.wallet,
            amount=Decimal("500.00"),
            method="card",
            destination=self.destination,
        )

        self.assertEqual(withdrawal.status, Withdrawal.WithdrawalStatus.PENDING)
        self.assertEqual(withdrawal.amount, Decimal("500.00"))

    def test_withdrawal_fee_calculated(self):
        """Withdrawal fee should be calculated based on method."""
        service = WithdrawalService()
        withdrawal = service.create_withdrawal(
            wallet=self.wallet,
            amount=Decimal("1000.00"),
            method="card",
            destination=self.destination,
        )

        # Card withdrawal has a fixed fee of 50 RUB by default
        self.assertGreaterEqual(withdrawal.fee, Decimal("0.00"))
        self.assertEqual(withdrawal.net_amount, withdrawal.amount - withdrawal.fee)

    def test_withdrawal_net_amount_is_correct(self):
        service = WithdrawalService()
        withdrawal = service.create_withdrawal(
            wallet=self.wallet,
            amount=Decimal("2000.00"),
            method="card",
            destination=self.destination,
        )

        self.assertLessEqual(withdrawal.net_amount, withdrawal.amount)
        self.assertGreater(withdrawal.net_amount, Decimal("0.00"))

    def test_multiple_withdrawals_track_hold(self):
        service = WithdrawalService()

        service.create_withdrawal(
            wallet=self.wallet,
            amount=Decimal("1000.00"),
            method="card",
            destination=self.destination,
        )
        service.create_withdrawal(
            wallet=self.wallet,
            amount=Decimal("2000.00"),
            method="card",
            destination=self.destination,
        )

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.available_balance, Decimal("2000.00"))
        self.assertEqual(self.wallet.hold_balance, Decimal("3000.00"))


class WithdrawalInsufficientBalanceTest(TestCase):
    """Test withdrawal with insufficient balance."""

    def setUp(self):
        self.master_user = User.objects.create_user(
            email="master_insuf@test.com",
            password="testpass123",
            role=User.Role.MASTER,
        )
        self.master = self.master_user.master_profile
        self.wallet = self.master.wallet
        self.wallet.available_balance = Decimal("500.00")
        self.wallet.save()

        self.destination = PayoutDestination.objects.create(
            master=self.master,
            destination_type=PayoutDestination.DestinationType.CARD,
            card_last_four="9999",
            card_type="Mastercard",
            is_default=True,
        )

    def test_withdrawal_exceeding_balance_raises_error(self):
        service = WithdrawalService()

        with self.assertRaises(ValueError) as ctx:
            service.create_withdrawal(
                wallet=self.wallet,
                amount=Decimal("1000.00"),
                method="card",
                destination=self.destination,
            )

        self.assertIn("Недостаточно средств", str(ctx.exception))

        # Wallet balance unchanged
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.available_balance, Decimal("500.00"))
        self.assertEqual(self.wallet.hold_balance, Decimal("0.00"))

    def test_withdrawal_below_minimum_raises_error(self):
        service = WithdrawalService()

        with self.assertRaises(ValueError) as ctx:
            service.create_withdrawal(
                wallet=self.wallet,
                amount=Decimal("50.00"),  # Below min of 100
                method="card",
                destination=self.destination,
            )

        self.assertIn("Минимальная сумма", str(ctx.exception))

    def test_withdrawal_exactly_at_balance(self):
        """Withdrawal equal to available balance should succeed."""
        service = WithdrawalService()
        withdrawal = service.create_withdrawal(
            wallet=self.wallet,
            amount=Decimal("500.00"),
            method="card",
            destination=self.destination,
        )

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.available_balance, Decimal("0.00"))
        self.assertEqual(self.wallet.hold_balance, Decimal("500.00"))


class WithdrawalOwnershipTest(TestCase):
    """Test that withdrawal API enforces ownership."""

    def setUp(self):
        self.master_user = User.objects.create_user(
            email="master_own@test.com",
            password="testpass123",
            first_name="Owner",
            last_name="Master",
            role=User.Role.MASTER,
        )
        self.master = self.master_user.master_profile
        self.wallet = self.master.wallet
        self.wallet.available_balance = Decimal("5000.00")
        self.wallet.save()

        self.destination = PayoutDestination.objects.create(
            master=self.master,
            destination_type=PayoutDestination.DestinationType.CARD,
            card_last_four="1111",
            card_type="МИР",
            is_default=True,
            is_verified=True,
        )

        self.other_master_user = User.objects.create_user(
            email="other_master@test.com",
            password="testpass123",
            first_name="Other",
            last_name="Master",
            role=User.Role.MASTER,
        )

        self.client_user = User.objects.create_user(
            email="client_own@test.com",
            password="testpass123",
            first_name="Client",
            last_name="User",
        )

    def test_client_cannot_access_withdrawals(self):
        """Non-master user should not be able to create withdrawal."""
        api_client = APIClient()
        api_client.force_authenticate(user=self.client_user)

        from django.urls import reverse

        url = reverse("withdrawal-list")
        response = api_client.post(url, {
            "amount": "1000.00",
            "destination_id": str(self.destination.id),
        })

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_master_cannot_use_foreign_destination(self):
        """A master should not be able to use another master's payout destination."""
        api_client = APIClient()
        api_client.force_authenticate(user=self.other_master_user)

        from django.urls import reverse

        url = reverse("withdrawal-list")
        response = api_client.post(url, {
            "amount": "1000.00",
            "destination_id": str(self.destination.id),
        })

        # Should fail — destination belongs to different master
        self.assertIn(
            response.status_code,
            [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN],
        )

    def test_owner_can_view_own_withdrawals(self):
        """Master should only see their own withdrawals."""
        service = WithdrawalService()
        service.create_withdrawal(
            wallet=self.wallet,
            amount=Decimal("1000.00"),
            method="card",
            destination=self.destination,
        )

        api_client = APIClient()
        api_client.force_authenticate(user=self.master_user)

        from django.urls import reverse

        url = reverse("withdrawal-list")
        response = api_client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        # Should see the withdrawal we created
        if isinstance(results, list):
            self.assertEqual(len(results), 1)

    def test_other_master_sees_empty_withdrawals(self):
        """Another master should not see first master's withdrawals."""
        service = WithdrawalService()
        service.create_withdrawal(
            wallet=self.wallet,
            amount=Decimal("1000.00"),
            method="card",
            destination=self.destination,
        )

        api_client = APIClient()
        api_client.force_authenticate(user=self.other_master_user)

        from django.urls import reverse

        url = reverse("withdrawal-list")
        response = api_client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        if isinstance(results, list):
            self.assertEqual(len(results), 0)


class WithdrawalRejectionTest(TestCase):
    """Test that rejecting a withdrawal returns funds to available balance."""

    def setUp(self):
        self.master_user = User.objects.create_user(
            email="master_reject@test.com",
            password="testpass123",
            role=User.Role.MASTER,
        )
        self.master = self.master_user.master_profile
        self.wallet = self.master.wallet
        self.wallet.available_balance = Decimal("3000.00")
        self.wallet.save()

        self.destination = PayoutDestination.objects.create(
            master=self.master,
            destination_type=PayoutDestination.DestinationType.CARD,
            card_last_four="5555",
            card_type="Mastercard",
            is_default=True,
        )

    def test_reject_withdrawal_returns_funds(self):
        service = WithdrawalService()
        withdrawal = service.create_withdrawal(
            wallet=self.wallet,
            amount=Decimal("1000.00"),
            method="card",
            destination=self.destination,
        )

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.available_balance, Decimal("2000.00"))
        self.assertEqual(self.wallet.hold_balance, Decimal("1000.00"))

        service.reject_withdrawal(withdrawal, "Test rejection reason")

        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.status, Withdrawal.WithdrawalStatus.REJECTED)
        self.assertEqual(withdrawal.rejection_reason, "Test rejection reason")

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.available_balance, Decimal("3000.00"))
        self.assertEqual(self.wallet.hold_balance, Decimal("0.00"))


class WithdrawalCompletionTest(TestCase):
    """Test that completing a withdrawal updates totals correctly."""

    def setUp(self):
        self.master_user = User.objects.create_user(
            email="master_complete@test.com",
            password="testpass123",
            role=User.Role.MASTER,
        )
        self.master = self.master_user.master_profile
        self.wallet = self.master.wallet
        self.wallet.available_balance = Decimal("5000.00")
        self.wallet.save()

        self.destination = PayoutDestination.objects.create(
            master=self.master,
            destination_type=PayoutDestination.DestinationType.CARD,
            card_last_four="7777",
            card_type="Visa",
            is_default=True,
        )

    def test_complete_withdrawal_updates_totals(self):
        service = WithdrawalService()
        withdrawal = service.create_withdrawal(
            wallet=self.wallet,
            amount=Decimal("2000.00"),
            method="card",
            destination=self.destination,
        )

        service.complete_withdrawal(withdrawal)

        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.status, Withdrawal.WithdrawalStatus.COMPLETED)
        self.assertIsNotNone(withdrawal.completed_at)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.hold_balance, Decimal("0.00"))
        self.assertGreater(self.wallet.total_withdrawn, Decimal("0.00"))
        self.assertEqual(self.wallet.total_withdrawn, withdrawal.net_amount)

    def test_complete_withdrawal_available_balance_unchanged(self):
        """Completing withdrawal should not change available_balance —
        it was already deducted when the withdrawal was created."""
        service = WithdrawalService()
        withdrawal = service.create_withdrawal(
            wallet=self.wallet,
            amount=Decimal("1000.00"),
            method="card",
            destination=self.destination,
        )

        self.wallet.refresh_from_db()
        available_after_create = self.wallet.available_balance

        service.complete_withdrawal(withdrawal)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.available_balance, available_after_create)


class WalletFundReleaseTest(TestCase):
    """Test releasing held payment funds to available balance."""

    def setUp(self):
        self.client_user = User.objects.create_user(
            email="client_release@test.com",
            password="testpass123",
            first_name="Client",
            last_name="Release",
        )
        self.master_user = User.objects.create_user(
            email="master_release@test.com",
            password="testpass123",
            first_name="Master",
            last_name="Release",
            role=User.Role.MASTER,
        )
        self.master = self.master_user.master_profile
        self.wallet = self.master.wallet

    def test_release_funds_moves_pending_to_available(self):
        """After hold period, pending funds should move to available."""
        payment = Payment.objects.create(
            client=self.client_user,
            master=self.master,
            payment_type=Payment.PaymentType.FULL_PAYMENT,
            amount=Decimal("1000.00"),
            status=Payment.PaymentStatus.PENDING,
        )

        # Process payment
        service = PaymentService()
        service.process_successful_payment(payment, "bank_card")

        self.wallet.refresh_from_db()
        self.assertGreater(self.wallet.pending_balance, Decimal("0.00"))
        available_before = self.wallet.available_balance

        # Set available_at to past to simulate hold period expiry
        from django.utils import timezone

        payment.refresh_from_db()
        payment.available_at = timezone.now() - timezone.timedelta(hours=1)
        payment.save()

        # Release funds
        service.release_held_funds(payment)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.pending_balance, Decimal("0.00"))
        self.assertGreater(self.wallet.available_balance, available_before)

    def test_release_funds_not_triggered_before_hold_period(self):
        """Funds should not be released if hold period has not expired."""
        payment = Payment.objects.create(
            client=self.client_user,
            master=self.master,
            payment_type=Payment.PaymentType.FULL_PAYMENT,
            amount=Decimal("1000.00"),
            status=Payment.PaymentStatus.PENDING,
        )

        service = PaymentService()
        service.process_successful_payment(payment, "bank_card")

        self.wallet.refresh_from_db()
        pending_after = self.wallet.pending_balance

        # available_at is set to future (3 days from now by default)
        # Calling release_held_funds should be a no-op
        payment.refresh_from_db()
        service.release_held_funds(payment)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.pending_balance, pending_after)
