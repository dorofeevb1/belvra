"""
API views for payment processing.
"""

import logging
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Avg, Sum
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework import generics, permissions, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from django.db import transaction

from apps.appointments.models import Appointment
from apps.payments.models import Payment, PayoutDestination, Wallet, Withdrawal
from apps.payments.serializers import (
    CreatePaymentSerializer,
    CreatePayoutDestinationSerializer,
    CreateWithdrawalSerializer,
    PaymentSerializer,
    PayoutDestinationSerializer,
    RefundSerializer,
    WalletSerializer,
    WalletStatsSerializer,
    WebhookPaymentSerializer,
    WithdrawalSerializer,
)
from apps.payments.services import PaymentService, TBankService, WithdrawalService, YooKassaService

logger = logging.getLogger(__name__)


class IsMaster(permissions.BasePermission):
    """Permission check for master users."""

    def has_permission(self, request, view):
        return hasattr(request.user, "master_profile")


class IsClient(permissions.BasePermission):
    """Permission check for client users."""

    def has_permission(self, request, view):
        return request.user.is_authenticated


class PaymentFilter(filters.FilterSet):
    """Filter for payments."""

    status = filters.ChoiceFilter(choices=Payment.PaymentStatus.choices)
    payment_type = filters.ChoiceFilter(choices=Payment.PaymentType.choices)
    payment_method = filters.ChoiceFilter(choices=Payment.PaymentMethod.choices)
    date_from = filters.DateFilter(field_name="created_at", lookup_expr="gte")
    date_to = filters.DateFilter(field_name="created_at", lookup_expr="lte")
    min_amount = filters.NumberFilter(field_name="amount", lookup_expr="gte")
    max_amount = filters.NumberFilter(field_name="amount", lookup_expr="lte")

    class Meta:
        model = Payment
        fields = ["status", "payment_type", "payment_method", "date_from", "date_to"]


class WalletView(generics.RetrieveUpdateAPIView):
    """View for master wallet."""

    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated, IsMaster]

    def get_object(self):
        with transaction.atomic():
            wallet, created = Wallet.objects.get_or_create(
                master=self.request.user.master_profile,
                defaults={
                    "available_balance": Decimal("0.00"),
                    "pending_balance": Decimal("0.00"),
                }
            )
        return wallet


class WalletStatsView(views.APIView):
    """View for wallet statistics."""

    permission_classes = [permissions.IsAuthenticated, IsMaster]

    def get(self, request):
        """Get wallet statistics for different periods."""
        master = request.user.master_profile
        now = timezone.now()

        periods = {
            "today": now.replace(hour=0, minute=0, second=0, microsecond=0),
            "week": now - timedelta(days=7),
            "month": now - timedelta(days=30),
            "year": now - timedelta(days=365),
        }

        stats = []
        for period_name, start_date in periods.items():
            payments = Payment.objects.filter(
                master=master,
                status=Payment.PaymentStatus.SUCCEEDED,
                paid_at__gte=start_date
            )

            aggregates = payments.aggregate(
                total=Sum("amount"),
                avg=Avg("amount"),
                commission=Sum("commission"),
                net=Sum("net_amount"),
            )

            stats.append({
                "period": period_name,
                "total_earnings": aggregates["total"] or Decimal("0.00"),
                "total_payments": payments.count(),
                "average_payment": aggregates["avg"] or Decimal("0.00"),
                "commission_paid": aggregates["commission"] or Decimal("0.00"),
                "net_earnings": aggregates["net"] or Decimal("0.00"),
            })

        serializer = WalletStatsSerializer(stats, many=True)
        return Response(serializer.data)


class PaymentViewSet(ModelViewSet):
    """ViewSet for payments."""

    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = PaymentFilter

    def get_queryset(self):
        user = self.request.user

        # Master sees their received payments
        if hasattr(user, "master_profile"):
            return Payment.objects.filter(
                master=user.master_profile
            ).select_related(
                "client", "master__user", "appointment__service", "appointment__master_service"
            )

        # Client sees their made payments
        return Payment.objects.filter(
            client=user
        ).select_related(
            "client", "master__user", "appointment__service", "appointment__master_service"
        )

    def get_serializer_class(self):
        if self.action == "create":
            return CreatePaymentSerializer
        if self.action == "refund":
            return RefundSerializer
        return PaymentSerializer

    def create(self, request, *args, **kwargs):
        """Disabled — оплата услуг через сайт не поддерживается."""
        return Response(
            {"error": "Оплата услуг через сайт отключена. Оплата производится напрямую между клиентом и мастером."},
            status=status.HTTP_403_FORBIDDEN
        )

    @action(detail=True, methods=["post"])
    def refund(self, request, pk=None):
        """Disabled — возвраты через сайт не поддерживаются."""
        return Response(
            {"error": "Возвраты через сайт отключены."},
            status=status.HTTP_403_FORBIDDEN
        )

    @action(detail=True, methods=["get"])
    def get_status(self, request, pk=None):
        """Get payment status from payment provider."""
        payment = self.get_object()

        if not payment.external_payment_id:
            return Response(
                {"error": "Платёж ещё не создан в платёжной системе"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if payment.payment_provider == Payment.PaymentProvider.TINKOFF:
            service = TBankService()
        else:
            service = YooKassaService()

        payment_status = service.get_payment_status(payment.external_payment_id)
        return Response(payment_status)

    @action(detail=True, methods=["post"], url_path="confirm-test")
    def confirm_test(self, request, pk=None):
        """Confirm a test payment (only works for test mode payments)."""
        payment = self.get_object()

        # Check if this is a test payment
        if not payment.payment_metadata.get("test_mode"):
            return Response(
                {"error": "Это не тестовый платёж"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if payment.status != Payment.PaymentStatus.PENDING:
            return Response(
                {"error": "Платёж уже обработан"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Process as successful payment
        payment_service = PaymentService()
        payment_service.process_successful_payment(payment, payment_method="bank_card")

        return Response(PaymentSerializer(payment).data)


class ClientPaymentListView(generics.ListAPIView):
    """List payments for current client."""

    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = PaymentFilter

    def get_queryset(self):
        return Payment.objects.filter(client=self.request.user)


class MasterPaymentListView(generics.ListAPIView):
    """List payments for current master."""

    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated, IsMaster]
    filterset_class = PaymentFilter

    def get_queryset(self):
        return Payment.objects.filter(
            master=self.request.user.master_profile
        ).select_related("client", "appointment")


class PayoutDestinationViewSet(ModelViewSet):
    """ViewSet for payout destinations."""

    serializer_class = PayoutDestinationSerializer
    permission_classes = [permissions.IsAuthenticated, IsMaster]

    def get_queryset(self):
        return PayoutDestination.objects.filter(master=self.request.user.master_profile)

    def get_serializer_class(self):
        if self.action == "create":
            return CreatePayoutDestinationSerializer
        return PayoutDestinationSerializer

    def create(self, request, *args, **kwargs):
        """Add a new payout destination."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        master = request.user.master_profile

        destination_data = {
            "master": master,
            "destination_type": data["destination_type"],
            "is_default": data.get("is_default", False),
        }

        if data["destination_type"] == PayoutDestination.DestinationType.CARD:
            card_number = data["card_number"].replace(" ", "")
            destination_data["card_last_four"] = card_number[-4:]
            destination_data["card_type"] = self._detect_card_type(card_number)
            # In production, card_number would be tokenized via YooKassa
            destination_data["payout_token"] = f"card_token_{card_number[-4:]}"

        elif data["destination_type"] == PayoutDestination.DestinationType.YOOMONEY:
            destination_data["yoomoney_account"] = data["yoomoney_account"]

        elif data["destination_type"] == PayoutDestination.DestinationType.BANK_ACCOUNT:
            destination_data["bank_name"] = data.get("bank_name", "")
            destination_data["bik"] = data["bik"]
            destination_data["account_number"] = data["account_number"]

        destination = PayoutDestination.objects.create(**destination_data)

        return Response(
            PayoutDestinationSerializer(destination).data,
            status=status.HTTP_201_CREATED
        )

    def _detect_card_type(self, card_number: str) -> str:
        """Detect card type by first digits."""
        if card_number.startswith("4"):
            return "Visa"
        elif card_number.startswith(("51", "52", "53", "54", "55")):
            return "Mastercard"
        elif card_number.startswith("2"):
            return "МИР"
        return "Unknown"

    @action(detail=True, methods=["post"])
    def set_default(self, request, pk=None):
        """Set destination as default."""
        destination = self.get_object()
        if destination.master != request.user.master_profile:
            return Response(
                {"error": "Нет прав для изменения этого способа выплаты"},
                status=status.HTTP_403_FORBIDDEN
            )
        # Unset previous default
        PayoutDestination.objects.filter(
            master=request.user.master_profile,
            is_default=True
        ).exclude(id=destination.id).update(is_default=False)
        destination.is_default = True
        destination.save()
        return Response(PayoutDestinationSerializer(destination).data)


class WithdrawalFilter(filters.FilterSet):
    """Filter for withdrawals."""

    status = filters.ChoiceFilter(choices=Withdrawal.WithdrawalStatus.choices)
    method = filters.ChoiceFilter(choices=Withdrawal.WithdrawalMethod.choices)
    date_from = filters.DateFilter(field_name="created_at", lookup_expr="gte")
    date_to = filters.DateFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = Withdrawal
        fields = ["status", "method", "date_from", "date_to"]


class WithdrawalViewSet(ModelViewSet):
    """ViewSet for withdrawals."""

    serializer_class = WithdrawalSerializer
    permission_classes = [permissions.IsAuthenticated, IsMaster]
    filterset_class = WithdrawalFilter

    def get_queryset(self):
        return Withdrawal.objects.filter(wallet__master=self.request.user.master_profile)

    def get_serializer_class(self):
        if self.action == "create":
            return CreateWithdrawalSerializer
        return WithdrawalSerializer

    def create(self, request, *args, **kwargs):
        """Create a new withdrawal request."""
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        master = request.user.master_profile
        wallet, _ = Wallet.objects.get_or_create(master=master)
        destination = PayoutDestination.objects.get(id=data["destination_id"], master=master)

        withdrawal_service = WithdrawalService()
        withdrawal = withdrawal_service.create_withdrawal(
            wallet=wallet,
            amount=data["amount"],
            method=destination.destination_type,
            destination=destination,
        )

        return Response(
            WithdrawalSerializer(withdrawal).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a pending withdrawal."""
        withdrawal = self.get_object()

        if withdrawal.status != Withdrawal.WithdrawalStatus.PENDING:
            return Response(
                {"error": "Можно отменить только ожидающий запрос"},
                status=status.HTTP_400_BAD_REQUEST
            )

        withdrawal_service = WithdrawalService()
        withdrawal_service.reject_withdrawal(withdrawal, "Отменено пользователем")

        return Response(WithdrawalSerializer(withdrawal).data)


class TransactionListView(views.APIView):
    """
    Transaction view that computes transactions from completed appointments.
    This provides a financial summary view for masters.
    """

    permission_classes = [permissions.IsAuthenticated, IsMaster]

    def get(self, request):
        """Get list of transactions (completed appointments with financial data)."""
        master = request.user.master_profile

        # Get completed appointments
        appointments = Appointment.objects.filter(
            master=master,
            status=Appointment.Status.COMPLETED
        ).select_related("client", "service", "master_service").order_by("-date", "-end_time")

        # Calculate transactions
        transactions = []
        platform_fee_rate = Decimal(str(settings.PLATFORM_COMMISSION_RATE)) if hasattr(settings, 'PLATFORM_COMMISSION_RATE') else Decimal("0.05")

        for apt in appointments:
            price = apt.price or Decimal("0")
            materials_cost = Decimal("0")  # Would be tracked in appointment if needed

            # Check if payment exists and is successful
            successful_payment = apt.payments.filter(
                status=Payment.PaymentStatus.SUCCEEDED
            ).first()

            if successful_payment:
                platform_fee = successful_payment.commission
                net_profit = successful_payment.net_amount
                payment_status = "paid"
            else:
                # Calculate estimated values
                platform_fee = price * platform_fee_rate
                net_profit = price - materials_cost - platform_fee
                payment_status = "pending"

            transactions.append({
                "id": str(apt.id),
                "master_id": str(master.id),
                "appointment_id": str(apt.id),
                "client_name": apt.client.full_name if apt.client else "Клиент",
                "service_name": apt.master_service.name if apt.master_service else (apt.service.name if apt.service else "Услуга"),
                "date": apt.date.isoformat(),
                "income": float(price),
                "materials_cost": float(materials_cost),
                "platform_fee": float(platform_fee),
                "net_profit": float(net_profit),
                "status": payment_status,
                "created_at": apt.created_at.isoformat()
            })

        return Response(transactions)


class TransactionSummaryView(views.APIView):
    """Financial summary for master."""

    permission_classes = [permissions.IsAuthenticated, IsMaster]

    def get(self, request):
        """Get financial summary."""
        master = request.user.master_profile

        # Get wallet
        wallet = getattr(master, 'wallet', None)

        # Calculate totals from successful payments
        successful_payments = Payment.objects.filter(
            master=master,
            status=Payment.PaymentStatus.SUCCEEDED
        )

        total_aggregates = successful_payments.aggregate(
            total_earned=Sum("net_amount"),
            total_commission=Sum("commission")
        )

        # Get pending amount (completed appointments without successful payment)
        pending_appointments = Appointment.objects.filter(
            master=master,
            status=Appointment.Status.COMPLETED
        ).exclude(
            payments__status=Payment.PaymentStatus.SUCCEEDED
        ).aggregate(
            pending=Sum("price")
        )

        # Get last withdrawal
        last_withdrawal = Withdrawal.objects.filter(
            wallet__master=master,
            status=Withdrawal.WithdrawalStatus.COMPLETED
        ).order_by("-completed_at").first()

        return Response({
            "total_profit": float(total_aggregates["total_earned"] or 0),
            "pending_amount": float(pending_appointments["pending"] or 0),
            "last_payout": float(last_withdrawal.amount if last_withdrawal else 0),
            "last_payout_date": last_withdrawal.completed_at.isoformat() if last_withdrawal and last_withdrawal.completed_at else None,
            "available_balance": float(wallet.available_balance if wallet else 0),
            "total_commission_paid": float(total_aggregates["total_commission"] or 0)
        })


class YooKassaWebhookView(views.APIView):
    """Webhook handler for YooKassa notifications."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        """Handle YooKassa webhook notification."""
        # Verify signature
        yookassa = YooKassaService()
        signature = request.headers.get("X-YooKassa-Signature", "")

        if settings.YOOKASSA_WEBHOOK_SECRET:
            if not signature:
                logger.warning("Missing webhook signature")
                return Response(status=status.HTTP_401_UNAUTHORIZED)
            if not yookassa.verify_webhook_signature(request.body, signature):
                logger.warning("Invalid webhook signature")
                return Response(status=status.HTTP_401_UNAUTHORIZED)
        else:
            logger.warning("YOOKASSA_WEBHOOK_SECRET not configured — skipping signature check")

        # Parse and validate payload
        serializer = WebhookPaymentSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Invalid webhook payload: {serializer.errors}")
            return Response(status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        event = data["event"]
        obj = data["object"]

        logger.info(f"Received webhook: {event}")

        try:
            if event == "payment.succeeded":
                self._handle_payment_succeeded(obj)
            elif event == "payment.canceled":
                self._handle_payment_canceled(obj)
            elif event == "refund.succeeded":
                self._handle_refund_succeeded(obj)
            elif event == "payout.succeeded":
                self._handle_payout_succeeded(obj)
            elif event == "payout.canceled":
                self._handle_payout_canceled(obj)

        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(status=status.HTTP_200_OK)

    def _handle_payment_succeeded(self, obj: dict):
        """Handle successful payment."""
        payment_id = obj.get("metadata", {}).get("payment_id")
        if not payment_id:
            logger.warning("No payment_id in metadata")
            return

        try:
            payment = Payment.objects.get(id=payment_id)
        except Payment.DoesNotExist:
            logger.error(f"Payment {payment_id} not found")
            return

        # Idempotency: skip if already processed
        if payment.status == Payment.PaymentStatus.SUCCEEDED:
            logger.info(f"Payment {payment_id} already succeeded, skipping duplicate webhook")
            return

        payment_method = obj.get("payment_method", {}).get("type")

        payment_service = PaymentService()
        payment_service.process_successful_payment(payment, payment_method)

        logger.info(f"Processed successful payment {payment_id}")

    def _handle_payment_canceled(self, obj: dict):
        """Handle canceled payment."""
        payment_id = obj.get("metadata", {}).get("payment_id")
        if not payment_id:
            return

        try:
            payment = Payment.objects.get(id=payment_id)
            payment.status = Payment.PaymentStatus.CANCELLED
            payment.payment_metadata["cancellation_details"] = obj.get("cancellation_details", {})
            payment.save()
            logger.info(f"Canceled payment {payment_id}")
        except Payment.DoesNotExist:
            logger.error(f"Payment {payment_id} not found")

    def _handle_refund_succeeded(self, obj: dict):
        """Handle successful refund."""
        payment_id = obj.get("payment_id")
        if not payment_id:
            return

        try:
            payment = Payment.objects.get(external_payment_id=payment_id)
            refund_amount = Decimal(obj.get("amount", {}).get("value", "0"))

            payment.refunded_amount += refund_amount
            payment.refunded_at = timezone.now()

            if payment.refunded_amount >= payment.amount:
                payment.status = Payment.PaymentStatus.REFUNDED
            else:
                payment.status = Payment.PaymentStatus.PARTIALLY_REFUNDED

            payment.save()
            logger.info(f"Processed refund for payment {payment.id}")
        except Payment.DoesNotExist:
            logger.error(f"Payment with external_id {payment_id} not found")

    def _handle_payout_succeeded(self, obj: dict):
        """Handle successful payout."""
        withdrawal_id = obj.get("metadata", {}).get("withdrawal_id")
        if not withdrawal_id:
            return

        try:
            withdrawal = Withdrawal.objects.get(id=withdrawal_id)
            withdrawal_service = WithdrawalService()
            withdrawal_service.complete_withdrawal(withdrawal)
            logger.info(f"Completed withdrawal {withdrawal_id}")
        except Withdrawal.DoesNotExist:
            logger.error(f"Withdrawal {withdrawal_id} not found")

    def _handle_payout_canceled(self, obj: dict):
        """Handle canceled payout."""
        withdrawal_id = obj.get("metadata", {}).get("withdrawal_id")
        if not withdrawal_id:
            return

        try:
            withdrawal = Withdrawal.objects.get(id=withdrawal_id)
            reason = obj.get("cancellation_details", {}).get("reason", "Отклонено провайдером")
            withdrawal_service = WithdrawalService()
            withdrawal_service.reject_withdrawal(withdrawal, reason)
            logger.info(f"Canceled withdrawal {withdrawal_id}")
        except Withdrawal.DoesNotExist:
            logger.error(f"Withdrawal {withdrawal_id} not found")


class TBankNotificationView(views.APIView):
    """
    Webhook handler for T-Bank payment notifications.

    T-Bank sends POST with form/JSON data and expects HTTP 200 with body "OK".
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        """Handle T-Bank notification."""
        data = request.data
        tbank = TBankService()

        # Verify token signature
        if not tbank.test_mode and not tbank.verify_notification_token(data):
            logger.warning("Invalid T-Bank notification token")
            return Response("INVALID TOKEN", status=status.HTTP_401_UNAUTHORIZED)

        order_id = data.get("OrderId")
        tbank_status = data.get("Status")
        payment_id_tbank = str(data.get("PaymentId", ""))

        logger.info(f"T-Bank notification: OrderId={order_id}, Status={tbank_status}, PaymentId={payment_id_tbank}")

        if not order_id:
            logger.warning("T-Bank notification missing OrderId")
            return Response("OK", status=status.HTTP_200_OK)

        try:
            payment = Payment.objects.get(id=order_id)
        except Payment.DoesNotExist:
            logger.error(f"Payment with OrderId={order_id} not found")
            return Response("OK", status=status.HTTP_200_OK)

        # Update external payment ID if not set
        if payment_id_tbank and not payment.external_payment_id:
            payment.external_payment_id = payment_id_tbank
            payment.save(update_fields=["external_payment_id"])

        try:
            if tbank_status == "CONFIRMED":
                self._handle_confirmed(payment, data)
            elif tbank_status == "AUTHORIZED":
                self._handle_authorized(payment, data)
            elif tbank_status in ("REJECTED", "DEADLINE_EXPIRED"):
                self._handle_rejected(payment, tbank_status)
            elif tbank_status == "REVERSED":
                self._handle_reversed(payment)
            elif tbank_status in ("REFUNDED", "PARTIAL_REFUNDED"):
                self._handle_refunded(payment, data, tbank_status)
        except Exception as e:
            logger.error(f"Error processing T-Bank notification: {e}")

        # T-Bank requires response body "OK"
        return Response("OK", status=status.HTTP_200_OK)

    def _handle_confirmed(self, payment: Payment, data: dict):
        """Handle CONFIRMED status — payment completed."""
        if payment.status == Payment.PaymentStatus.SUCCEEDED:
            logger.info(f"Payment {payment.id} already succeeded, skipping")
            return

        payment_method = "bank_card"
        if data.get("Pan"):
            payment.payment_metadata["card_pan"] = data["Pan"]
        if data.get("CardId"):
            payment.payment_metadata["card_id"] = str(data["CardId"])
        payment.save(update_fields=["payment_metadata"])

        payment_service = PaymentService()
        payment_service.process_successful_payment(payment, payment_method)
        logger.info(f"T-Bank: confirmed payment {payment.id}")

    def _handle_authorized(self, payment: Payment, data: dict):
        """Handle AUTHORIZED status — funds held (two-stage)."""
        payment.status = Payment.PaymentStatus.PROCESSING
        payment.payment_metadata["tbank_status"] = "AUTHORIZED"
        if data.get("Pan"):
            payment.payment_metadata["card_pan"] = data["Pan"]
        payment.save()
        logger.info(f"T-Bank: authorized payment {payment.id}")

    def _handle_rejected(self, payment: Payment, tbank_status: str):
        """Handle REJECTED or DEADLINE_EXPIRED."""
        if payment.status in (Payment.PaymentStatus.SUCCEEDED, Payment.PaymentStatus.REFUNDED):
            return
        payment.status = Payment.PaymentStatus.FAILED
        payment.payment_metadata["tbank_status"] = tbank_status
        payment.save()
        logger.info(f"T-Bank: rejected payment {payment.id}, status={tbank_status}")

    def _handle_reversed(self, payment: Payment):
        """Handle REVERSED — full cancellation of authorized payment."""
        payment.status = Payment.PaymentStatus.CANCELLED
        payment.payment_metadata["tbank_status"] = "REVERSED"
        payment.save()
        logger.info(f"T-Bank: reversed payment {payment.id}")

    def _handle_refunded(self, payment: Payment, data: dict, tbank_status: str):
        """Handle REFUNDED or PARTIAL_REFUNDED."""
        amount_kopecks = data.get("Amount", 0)
        refund_amount = Decimal(str(amount_kopecks)) / 100

        payment.refunded_amount = refund_amount
        payment.refunded_at = timezone.now()

        if tbank_status == "REFUNDED":
            payment.status = Payment.PaymentStatus.REFUNDED
        else:
            payment.status = Payment.PaymentStatus.PARTIALLY_REFUNDED

        payment.payment_metadata["tbank_status"] = tbank_status
        payment.save()
        logger.info(f"T-Bank: refunded payment {payment.id}, amount={refund_amount}")
