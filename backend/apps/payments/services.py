"""
Payment services for YooKassa and T-Bank integration.
"""

import hashlib
import hmac
import logging
import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Optional

import requests as http_requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from yookassa import Configuration, Payment as YooKassaPayment, Payout, Refund
from yookassa.domain.common import ConfirmationType
from yookassa.domain.models import Amount, Receipt, ReceiptItem
from yookassa.domain.request import PaymentRequest, RefundRequest

from apps.appointments.models import Appointment
from apps.core.notifications import NotificationService
from apps.payments.models import Payment, PayoutDestination, Wallet, Withdrawal

logger = logging.getLogger(__name__)


class YooKassaService:
    """Service for YooKassa payment processing."""

    def __init__(self):
        """Initialize YooKassa configuration."""
        self.test_mode = not settings.YOOKASSA_SHOP_ID or not settings.YOOKASSA_SECRET_KEY
        if not self.test_mode:
            Configuration.account_id = settings.YOOKASSA_SHOP_ID
            Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

    def create_payment(
        self,
        payment: Payment,
        return_url: str,
        description: Optional[str] = None,
        save_payment_method: bool = False,
        payment_method: Optional[str] = None
    ) -> dict:
        """
        Create a payment in YooKassa.

        Args:
            payment: Payment model instance
            return_url: URL to redirect after payment
            description: Payment description
            save_payment_method: Whether to save payment method for future use
            payment_method: Preferred payment method ('sbp', 'bank_card', etc.)

        Returns:
            dict with payment_id and confirmation_url
        """
        try:
            idempotency_key = str(payment.id)

            # Test mode - return mock response
            if self.test_mode:
                mock_payment_id = f"test_{uuid.uuid4().hex[:16]}"
                # Add payment_id to URL so frontend can confirm the test payment
                separator = "&" if "?" in return_url else "?"
                mock_confirmation_url = f"{return_url}{separator}test_payment={mock_payment_id}&payment_id={payment.id}"

                payment.external_payment_id = mock_payment_id
                payment.confirmation_url = mock_confirmation_url
                payment.status = Payment.PaymentStatus.PENDING
                payment.payment_metadata = {
                    "test_mode": True,
                    "created_at": str(timezone.now()),
                }
                payment.save()

                logger.info(f"Created TEST payment {mock_payment_id} for payment {payment.id}")

                return {
                    "payment_id": mock_payment_id,
                    "confirmation_url": mock_confirmation_url,
                    "status": "pending",
                    "test_mode": True,
                }

            payment_data = {
                "amount": Amount(
                    value=str(payment.amount),
                    currency="RUB"
                ),
                "confirmation": {
                    "type": ConfirmationType.REDIRECT,
                    "return_url": return_url
                },
                "capture": True,  # Auto-capture
                "description": description or f"Оплата услуги #{payment.appointment_id}",
                "metadata": {
                    "payment_id": str(payment.id),
                    "appointment_id": str(payment.appointment_id) if payment.appointment_id else None,
                    "client_id": str(payment.client_id),
                    "master_id": str(payment.master_id),
                },
                "save_payment_method": save_payment_method,
            }

            # Add payment method if specified (for SBP, bank_card, etc.)
            if payment_method:
                payment_data["payment_method_data"] = {
                    "type": payment_method
                }

            # Add receipt for FZ-54 compliance
            if hasattr(settings, "YOOKASSA_SEND_RECEIPT") and settings.YOOKASSA_SEND_RECEIPT:
                receipt = self._create_receipt(payment)
                payment_data["receipt"] = receipt

            yoo_payment = YooKassaPayment.create(payment_data, idempotency_key)

            # Update payment with external data
            payment.external_payment_id = yoo_payment.id
            payment.confirmation_url = yoo_payment.confirmation.confirmation_url
            payment.status = Payment.PaymentStatus.PENDING
            payment.payment_metadata = {
                "yookassa_status": yoo_payment.status,
                "created_at": str(yoo_payment.created_at),
            }
            payment.save()

            logger.info(f"Created YooKassa payment {yoo_payment.id} for payment {payment.id}")

            return {
                "payment_id": yoo_payment.id,
                "confirmation_url": yoo_payment.confirmation.confirmation_url,
                "status": yoo_payment.status,
            }

        except Exception as e:
            logger.error(f"Error creating YooKassa payment: {e}")
            payment.status = Payment.PaymentStatus.FAILED
            payment.payment_metadata["error"] = str(e)
            payment.save()
            raise

    def _create_receipt(self, payment: Payment) -> dict:
        """Create receipt for FZ-54 compliance."""
        items = []

        if payment.appointment:
            # Get service name from master_service or service
            if payment.appointment.master_service:
                service_name = payment.appointment.master_service.name
            elif payment.appointment.service:
                service_name = payment.appointment.service.name
            else:
                service_name = "Услуга салона красоты"
        else:
            service_name = "Услуга салона красоты"

        items.append({
            "description": service_name[:128],  # Max 128 chars
            "quantity": "1.00",
            "amount": {
                "value": str(payment.amount),
                "currency": "RUB"
            },
            "vat_code": 1,  # НДС не облагается
            "payment_subject": "service",
            "payment_mode": "full_payment",
        })

        return {
            "customer": {
                "email": payment.client.email if payment.client.email else None,
                "phone": payment.client.phone if hasattr(payment.client, "phone") else None,
            },
            "items": items,
        }

    def get_payment_status(self, external_payment_id: str) -> dict:
        """Get payment status from YooKassa."""
        try:
            yoo_payment = YooKassaPayment.find_one(external_payment_id)
            return {
                "id": yoo_payment.id,
                "status": yoo_payment.status,
                "paid": yoo_payment.paid,
                "amount": yoo_payment.amount.value,
                "payment_method": yoo_payment.payment_method.type if yoo_payment.payment_method else None,
                "captured_at": str(yoo_payment.captured_at) if yoo_payment.captured_at else None,
            }
        except Exception as e:
            logger.error(f"Error getting payment status: {e}")
            raise

    def create_refund(
        self,
        payment: Payment,
        amount: Optional[Decimal] = None,
        description: Optional[str] = None
    ) -> dict:
        """
        Create a refund for a payment.

        Args:
            payment: Payment model instance
            amount: Refund amount (full refund if not specified)
            description: Refund description

        Returns:
            dict with refund status
        """
        try:
            refund_amount = amount or payment.amount
            idempotency_key = f"refund-{payment.id}"

            refund_data = {
                "payment_id": payment.external_payment_id,
                "amount": Amount(
                    value=str(refund_amount),
                    currency="RUB"
                ),
                "description": description or f"Возврат за услугу #{payment.appointment_id}",
            }

            yoo_refund = Refund.create(refund_data, idempotency_key)

            # Update payment
            payment.refunded_amount += Decimal(yoo_refund.amount.value)
            payment.refunded_at = timezone.now()

            if payment.refunded_amount >= payment.amount:
                payment.status = Payment.PaymentStatus.REFUNDED
            else:
                payment.status = Payment.PaymentStatus.PARTIALLY_REFUNDED

            payment.payment_metadata["refund_id"] = yoo_refund.id
            payment.save()

            logger.info(f"Created refund {yoo_refund.id} for payment {payment.id}")

            return {
                "refund_id": yoo_refund.id,
                "status": yoo_refund.status,
                "amount": yoo_refund.amount.value,
            }

        except Exception as e:
            logger.error(f"Error creating refund: {e}")
            raise

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        """
        Verify webhook signature from YooKassa.

        Args:
            body: Request body bytes
            signature: Signature from header

        Returns:
            bool indicating if signature is valid
        """
        secret = settings.YOOKASSA_WEBHOOK_SECRET
        expected_signature = hmac.new(
            secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected_signature, signature)


class TBankService:
    """Service for T-Bank (Tinkoff) e-acquiring payment processing."""

    def __init__(self):
        self.terminal_key = settings.TBANK_TERMINAL_KEY
        self.password = settings.TBANK_PASSWORD
        self.api_url = getattr(settings, "TBANK_API_URL", "https://securepay.tinkoff.ru/v2/")
        self.test_mode = not self.terminal_key or not self.password

    def _generate_token(self, params: dict) -> str:
        """
        Generate Token for T-Bank API request.

        Algorithm:
        1. Collect all root-level scalar params (exclude nested objects/arrays).
        2. Add Password.
        3. Sort alphabetically by key.
        4. Concatenate values only.
        5. SHA-256 hash.
        """
        token_params = {}
        for key, value in params.items():
            if key == "Token":
                continue
            # Only include scalar values (str, int, float, bool), skip dicts/lists
            if isinstance(value, (dict, list)):
                continue
            token_params[key] = str(value)

        token_params["Password"] = self.password

        # Sort by key and concatenate values
        sorted_keys = sorted(token_params.keys())
        values_string = "".join(token_params[key] for key in sorted_keys)

        return hashlib.sha256(values_string.encode("utf-8")).hexdigest()

    def _request(self, method: str, params: dict) -> dict:
        """Make a request to T-Bank API."""
        params["TerminalKey"] = self.terminal_key
        params["Token"] = self._generate_token(params)

        url = f"{self.api_url}{method}"
        response = http_requests.post(url, json=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        if not data.get("Success", False):
            error_code = data.get("ErrorCode", "unknown")
            error_msg = data.get("Message", "") or data.get("Details", "")
            raise Exception(f"T-Bank API error {error_code}: {error_msg}")

        return data

    def create_payment(
        self,
        payment: Payment,
        return_url: str,
        description: Optional[str] = None,
        save_payment_method: bool = False,
        payment_method: Optional[str] = None,
    ) -> dict:
        """
        Create a payment via T-Bank Init endpoint.

        Returns:
            dict with payment_id and confirmation_url
        """
        try:
            if self.test_mode:
                mock_payment_id = f"tbank_test_{uuid.uuid4().hex[:12]}"
                separator = "&" if "?" in return_url else "?"
                mock_url = f"{return_url}{separator}test_payment={mock_payment_id}&payment_id={payment.id}"

                payment.external_payment_id = mock_payment_id
                payment.confirmation_url = mock_url
                payment.status = Payment.PaymentStatus.PENDING
                payment.payment_metadata = {
                    "test_mode": True,
                    "provider": "tbank",
                    "created_at": str(timezone.now()),
                }
                payment.save()

                logger.info(f"Created TEST T-Bank payment {mock_payment_id} for payment {payment.id}")
                return {
                    "payment_id": mock_payment_id,
                    "confirmation_url": mock_url,
                    "status": "pending",
                    "test_mode": True,
                }

            # Amount in kopecks (integer)
            amount_kopecks = int(payment.amount * 100)

            params = {
                "Amount": amount_kopecks,
                "OrderId": str(payment.id),
                "Description": (description or f"Оплата услуги #{payment.appointment_id}")[:140],
                "SuccessURL": return_url,
                "FailURL": return_url,
                "DATA": {
                    "payment_id": str(payment.id),
                    "appointment_id": str(payment.appointment_id) if payment.appointment_id else "",
                    "client_id": str(payment.client_id),
                    "master_id": str(payment.master_id),
                },
            }

            if save_payment_method:
                params["Recurrent"] = "Y"
                params["CustomerKey"] = str(payment.client_id)

            # Add receipt for FZ-54 compliance
            if getattr(settings, "TBANK_SEND_RECEIPT", False):
                params["Receipt"] = self._create_receipt(payment)

            data = self._request("Init", params)

            payment.external_payment_id = str(data["PaymentId"])
            payment.confirmation_url = data["PaymentURL"]
            payment.status = Payment.PaymentStatus.PENDING
            payment.payment_metadata = {
                "provider": "tbank",
                "tbank_status": data.get("Status"),
                "created_at": str(timezone.now()),
            }
            payment.save()

            logger.info(f"Created T-Bank payment {data['PaymentId']} for payment {payment.id}")

            return {
                "payment_id": str(data["PaymentId"]),
                "confirmation_url": data["PaymentURL"],
                "status": data.get("Status", "NEW"),
            }

        except Exception as e:
            logger.error(f"Error creating T-Bank payment: {e}")
            payment.status = Payment.PaymentStatus.FAILED
            payment.payment_metadata["error"] = str(e)
            payment.save()
            raise

    def _create_receipt(self, payment: Payment) -> dict:
        """Create receipt for FZ-54 compliance (T-Bank format)."""
        if payment.appointment:
            if payment.appointment.master_service:
                service_name = payment.appointment.master_service.name
            elif payment.appointment.service:
                service_name = payment.appointment.service.name
            else:
                service_name = "Услуга салона красоты"
        else:
            service_name = "Услуга салона красоты"

        amount_kopecks = int(payment.amount * 100)
        taxation = getattr(settings, "TBANK_TAXATION", "usn_income")

        receipt = {
            "Taxation": taxation,
            "Items": [
                {
                    "Name": service_name[:128],
                    "Price": amount_kopecks,
                    "Quantity": 1.0,
                    "Amount": amount_kopecks,
                    "Tax": "none",
                    "PaymentMethod": "full_payment",
                    "PaymentObject": "service",
                }
            ],
        }

        if payment.client and payment.client.email:
            receipt["Email"] = payment.client.email
        if payment.client and hasattr(payment.client, "phone") and payment.client.phone:
            receipt["Phone"] = payment.client.phone

        return receipt

    def get_payment_status(self, external_payment_id: str) -> dict:
        """Get payment status from T-Bank via GetState."""
        try:
            data = self._request("GetState", {"PaymentId": external_payment_id})

            # Map T-Bank statuses to our format
            status_map = {
                "NEW": "pending",
                "AUTHORIZED": "waiting_for_capture",
                "CONFIRMED": "succeeded",
                "REJECTED": "canceled",
                "REVERSED": "canceled",
                "PARTIAL_REVERSED": "partially_refunded",
                "REFUNDED": "refunded",
                "PARTIAL_REFUNDED": "partially_refunded",
                "DEADLINE_EXPIRED": "canceled",
            }

            return {
                "id": str(data.get("PaymentId")),
                "status": status_map.get(data.get("Status"), data.get("Status")),
                "tbank_status": data.get("Status"),
                "amount": str(Decimal(data.get("Amount", 0)) / 100),
                "payment_method": "bank_card",
            }
        except Exception as e:
            logger.error(f"Error getting T-Bank payment status: {e}")
            raise

    def create_refund(
        self,
        payment: Payment,
        amount: Optional[Decimal] = None,
        description: Optional[str] = None,
    ) -> dict:
        """
        Create a refund via T-Bank Cancel endpoint.

        Works for both reversal (AUTHORIZED) and refund (CONFIRMED).
        """
        try:
            refund_amount = amount or payment.amount
            amount_kopecks = int(refund_amount * 100)

            params = {
                "PaymentId": payment.external_payment_id,
                "Amount": amount_kopecks,
            }

            if getattr(settings, "TBANK_SEND_RECEIPT", False):
                params["Receipt"] = self._create_receipt(payment)

            data = self._request("Cancel", params)

            payment.refunded_amount += refund_amount
            payment.refunded_at = timezone.now()

            if payment.refunded_amount >= payment.amount:
                payment.status = Payment.PaymentStatus.REFUNDED
            else:
                payment.status = Payment.PaymentStatus.PARTIALLY_REFUNDED

            payment.payment_metadata["refund_status"] = data.get("Status")
            payment.save()

            logger.info(f"Created T-Bank refund for payment {payment.id}, amount: {refund_amount}")

            return {
                "refund_id": str(data.get("PaymentId")),
                "status": data.get("Status"),
                "amount": str(refund_amount),
            }

        except Exception as e:
            logger.error(f"Error creating T-Bank refund: {e}")
            raise

    def verify_notification_token(self, params: dict) -> bool:
        """
        Verify T-Bank notification token.

        Same algorithm as _generate_token but applied to notification params.
        """
        received_token = params.get("Token", "")
        if not received_token:
            return False

        # Build params without Token and nested objects
        check_params = {}
        for key, value in params.items():
            if key == "Token":
                continue
            if isinstance(value, (dict, list)):
                continue
            check_params[key] = str(value)

        check_params["Password"] = self.password

        sorted_keys = sorted(check_params.keys())
        values_string = "".join(check_params[key] for key in sorted_keys)
        expected_token = hashlib.sha256(values_string.encode("utf-8")).hexdigest()

        return hmac.compare_digest(expected_token, received_token)


class PaymentService:
    """High-level payment service."""

    def __init__(self):
        self.yookassa = YooKassaService()
        self.tbank = TBankService()

    def _get_provider(self) -> str:
        """Get the active payment provider from settings."""
        return getattr(settings, "PAYMENT_PROVIDER", "tinkoff")

    def _get_provider_service(self, provider: str):
        """Get the payment service for the given provider."""
        if provider == "tinkoff":
            return self.tbank
        return self.yookassa

    @transaction.atomic
    def create_appointment_payment(
        self,
        appointment: Appointment,
        payment_type: str = Payment.PaymentType.FULL_PAYMENT,
        amount: Optional[Decimal] = None,
        return_url: str = None,
        payment_method: Optional[str] = None
    ) -> Payment:
        """
        Create a payment for an appointment.

        Routes to the active payment provider (T-Bank or YooKassa).
        """
        # Calculate amount
        if amount is None:
            if payment_type == Payment.PaymentType.PREPAYMENT:
                prepayment_percent = Decimal(str(getattr(settings, "PREPAYMENT_PERCENT", "0.20")))
                amount = appointment.price * prepayment_percent
            else:
                amount = appointment.price

        # Get service name from master_service or service
        if appointment.master_service:
            service_name = appointment.master_service.name
        elif appointment.service:
            service_name = appointment.service.name
        else:
            service_name = "Услуга"

        # Determine provider
        provider = self._get_provider()
        if provider == "tinkoff":
            payment_provider = Payment.PaymentProvider.TINKOFF
        else:
            payment_provider = Payment.PaymentProvider.YOOKASSA

        # Create payment record
        payment = Payment.objects.create(
            appointment=appointment,
            client=appointment.client,
            master=appointment.master,
            payment_type=payment_type,
            amount=amount,
            payment_provider=payment_provider,
            description=f"Оплата услуги: {service_name}"
        )

        # Create payment in provider
        if return_url is None:
            return_url = settings.PAYMENT_RETURN_URL

        provider_service = self._get_provider_service(provider)
        result = provider_service.create_payment(
            payment=payment,
            return_url=return_url,
            description=f"Оплата услуги: {service_name}",
            payment_method=payment_method,
        )

        return payment

    @transaction.atomic
    def process_successful_payment(self, payment: Payment, payment_method: str = None):
        """
        Process a successful payment.

        Updates payment status, creates wallet transaction,
        and schedules fund availability.
        """
        hold_days = getattr(settings, "PAYMENT_HOLD_DAYS", 3)

        payment.status = Payment.PaymentStatus.SUCCEEDED
        payment.paid_at = timezone.now()
        payment.available_at = timezone.now() + timedelta(days=hold_days)
        payment.payment_method = payment_method
        payment.save()

        # Update or create master wallet
        wallet, created = Wallet.objects.get_or_create(
            master=payment.master,
            defaults={
                "available_balance": Decimal("0.00"),
                "pending_balance": Decimal("0.00"),
            }
        )

        # Add to pending balance (will be available after hold period)
        wallet.pending_balance += payment.net_amount
        wallet.total_earned += payment.net_amount
        wallet.total_commission_paid += payment.commission
        wallet.save()

        # Update appointment status if exists
        if payment.appointment:
            if payment.payment_type == Payment.PaymentType.FULL_PAYMENT:
                payment.appointment.status = Appointment.Status.CONFIRMED
            payment.appointment.save()

        # Send notification to master about received payment
        if payment.master and payment.master.user:
            client_name = payment.client.full_name if payment.client else "Клиент"
            NotificationService.notify_payment_received(
                master_user=payment.master.user,
                client_name=client_name,
                amount=str(payment.amount),
                service_name=payment.description or "Услуга"
            )

        logger.info(f"Processed successful payment {payment.id}, net amount: {payment.net_amount}")

    @transaction.atomic
    def release_held_funds(self, payment: Payment):
        """Release held funds to available balance."""
        if payment.status != Payment.PaymentStatus.SUCCEEDED:
            return

        if payment.available_at and payment.available_at > timezone.now():
            return

        wallet = getattr(payment.master, "wallet", None)
        if not wallet:
            return
        wallet.pending_balance -= payment.net_amount
        wallet.available_balance += payment.net_amount
        wallet.save()

        logger.info(f"Released funds for payment {payment.id} to wallet {wallet.id}")

    @transaction.atomic
    def process_refund(self, payment: Payment, amount: Optional[Decimal] = None, reason: str = ""):
        """
        Process a refund for a payment.

        Args:
            payment: Payment to refund
            amount: Refund amount (full if not specified)
            reason: Refund reason
        """
        if payment.status not in [Payment.PaymentStatus.SUCCEEDED, Payment.PaymentStatus.PARTIALLY_REFUNDED]:
            raise ValueError("Cannot refund payment that is not succeeded")

        # Create refund via appropriate provider
        if payment.payment_provider == Payment.PaymentProvider.TINKOFF:
            result = self.tbank.create_refund(payment, amount, reason)
        else:
            result = self.yookassa.create_refund(payment, amount, reason)

        # Update wallet (lock row to prevent concurrent refund race condition)
        try:
            wallet = Wallet.objects.select_for_update().get(master=payment.master)
        except Wallet.DoesNotExist:
            logger.error(f"Wallet not found for master {payment.master.id} during refund of payment {payment.id}")
            return

        refund_amount = Decimal(result["amount"])

        # Calculate proportional commission refund
        if payment.amount > 0:
            commission_refund = (refund_amount / payment.amount) * payment.commission
        else:
            commission_refund = Decimal("0.00")
        net_refund = refund_amount - commission_refund

        # Deduct from wallet
        if wallet.available_balance >= net_refund:
            wallet.available_balance -= net_refund
        else:
            # If available balance is not enough, deduct from pending
            from_available = wallet.available_balance
            from_pending = net_refund - from_available
            wallet.available_balance = Decimal("0.00")
            wallet.pending_balance = max(Decimal("0.00"), wallet.pending_balance - from_pending)

        wallet.total_earned = max(Decimal("0.00"), wallet.total_earned - net_refund)
        wallet.total_commission_paid = max(Decimal("0.00"), wallet.total_commission_paid - commission_refund)
        wallet.save()

        # Send notification to client about refund
        if payment.client:
            service_name = ""
            if hasattr(payment, 'appointment') and payment.appointment:
                service_name = getattr(payment.appointment, 'service_name', '')
            NotificationService.notify_payment_refunded(
                client_user=payment.client,
                amount=str(refund_amount),
                service_name=service_name or "услуга"
            )

        logger.info(f"Processed refund for payment {payment.id}, amount: {refund_amount}")


class WithdrawalService:
    """Service for processing withdrawals."""

    def __init__(self):
        if settings.YOOKASSA_SHOP_ID and settings.YOOKASSA_SECRET_KEY:
            Configuration.account_id = settings.YOOKASSA_SHOP_ID
            Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

    @transaction.atomic
    def create_withdrawal(
        self,
        wallet: Wallet,
        amount: Decimal,
        method: str,
        destination: PayoutDestination
    ) -> Withdrawal:
        """
        Create a withdrawal request.

        Args:
            wallet: Master's wallet
            amount: Withdrawal amount
            method: Withdrawal method
            destination: Payout destination

        Returns:
            Withdrawal instance
        """
        min_withdrawal = getattr(settings, "MIN_WITHDRAWAL_AMOUNT", Decimal("100.00"))

        if amount < min_withdrawal:
            raise ValueError(f"Минимальная сумма вывода: {min_withdrawal} ₽")

        if amount > wallet.available_balance:
            raise ValueError("Недостаточно средств на балансе")

        # Create withdrawal record
        withdrawal = Withdrawal.objects.create(
            wallet=wallet,
            amount=amount,
            method=method,
            card_last_four=destination.card_last_four if destination.destination_type == "card" else None,
            destination_account=self._get_destination_account(destination),
        )

        # Reserve funds
        wallet.available_balance -= amount
        wallet.hold_balance += amount
        wallet.save()

        logger.info(f"Created withdrawal request {withdrawal.id} for {amount} ₽")

        return withdrawal

    def _get_destination_account(self, destination: PayoutDestination) -> str:
        """Get destination account string for display."""
        if destination.destination_type == PayoutDestination.DestinationType.CARD:
            return f"**** {destination.card_last_four}"
        elif destination.destination_type == PayoutDestination.DestinationType.YOOMONEY:
            return destination.yoomoney_account
        else:
            return f"{destination.bank_name} **** {destination.account_number[-4:]}"

    @transaction.atomic
    def process_withdrawal(self, withdrawal: Withdrawal, destination: PayoutDestination):
        """
        Process a withdrawal via YooKassa Payout.

        Args:
            withdrawal: Withdrawal instance
            destination: PayoutDestination with payout token
        """
        try:
            withdrawal.status = Withdrawal.WithdrawalStatus.PROCESSING
            withdrawal.processed_at = timezone.now()
            withdrawal.save()

            idempotency_key = str(withdrawal.id)

            payout_data = {
                "amount": {
                    "value": str(withdrawal.net_amount),
                    "currency": "RUB"
                },
                "payout_destination_data": self._get_payout_destination_data(destination),
                "description": f"Вывод средств #{withdrawal.id}",
                "metadata": {
                    "withdrawal_id": str(withdrawal.id),
                    "master_id": str(withdrawal.wallet.master_id),
                },
            }

            payout = Payout.create(payout_data, idempotency_key)

            withdrawal.external_payout_id = payout.id
            withdrawal.save()

            logger.info(f"Initiated payout {payout.id} for withdrawal {withdrawal.id}")

        except Exception as e:
            logger.error(f"Error processing withdrawal {withdrawal.id}: {e}")
            withdrawal.status = Withdrawal.WithdrawalStatus.FAILED
            withdrawal.rejection_reason = str(e)
            withdrawal.save()

            # Return funds to available balance
            wallet = withdrawal.wallet
            wallet.hold_balance -= withdrawal.amount
            wallet.available_balance += withdrawal.amount
            wallet.save()

            raise

    def _get_payout_destination_data(self, destination: PayoutDestination) -> dict:
        """Get payout destination data for YooKassa."""
        if destination.destination_type == PayoutDestination.DestinationType.CARD:
            return {
                "type": "bank_card",
                "card": {
                    "number": destination.payout_token  # Encrypted card token
                }
            }
        elif destination.destination_type == PayoutDestination.DestinationType.YOOMONEY:
            return {
                "type": "yoo_money",
                "account_number": destination.yoomoney_account
            }
        else:
            return {
                "type": "sbp",
                "bank_id": destination.bik,
                "phone": destination.account_number  # Phone for SBP
            }

    @transaction.atomic
    def complete_withdrawal(self, withdrawal: Withdrawal):
        """Mark withdrawal as completed."""
        withdrawal.status = Withdrawal.WithdrawalStatus.COMPLETED
        withdrawal.completed_at = timezone.now()
        withdrawal.save()

        # Move from hold to withdrawn
        wallet = withdrawal.wallet
        wallet.hold_balance -= withdrawal.amount
        wallet.total_withdrawn += withdrawal.net_amount
        wallet.save()

        logger.info(f"Completed withdrawal {withdrawal.id}")

    @transaction.atomic
    def reject_withdrawal(self, withdrawal: Withdrawal, reason: str):
        """Reject a withdrawal request."""
        withdrawal.status = Withdrawal.WithdrawalStatus.REJECTED
        withdrawal.rejection_reason = reason
        withdrawal.save()

        # Return funds
        wallet = withdrawal.wallet
        wallet.hold_balance -= withdrawal.amount
        wallet.available_balance += withdrawal.amount
        wallet.save()

        logger.info(f"Rejected withdrawal {withdrawal.id}: {reason}")
