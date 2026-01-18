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
from apps.payments.services import PaymentService, WithdrawalService, YooKassaService

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
            return Payment.objects.filter(master=user.master_profile)

        # Client sees their made payments
        return Payment.objects.filter(client=user)

    def get_serializer_class(self):
        if self.action == "create":
            return CreatePaymentSerializer
        if self.action == "refund":
            return RefundSerializer
        return PaymentSerializer

    def create(self, request, *args, **kwargs):
        """Create a new payment."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        appointment = Appointment.objects.get(id=data["appointment_id"])

        payment_service = PaymentService()
        payment = payment_service.create_appointment_payment(
            appointment=appointment,
            payment_type=data.get("payment_type", Payment.PaymentType.FULL_PAYMENT),
            amount=data.get("amount"),
            return_url=data.get("return_url", settings.PAYMENT_RETURN_URL),
            payment_method=data.get("payment_method"),
        )

        return Response(
            PaymentSerializer(payment).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"])
    def refund(self, request, pk=None):
        """Create a refund for a payment."""
        payment = self.get_object()

        serializer = RefundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment_service = PaymentService()
        payment_service.process_refund(
            payment=payment,
            amount=serializer.validated_data.get("amount"),
            reason=serializer.validated_data.get("reason", ""),
        )

        return Response(PaymentSerializer(payment).data)

    @action(detail=True, methods=["get"])
    def status(self, request, pk=None):
        """Get payment status from YooKassa."""
        payment = self.get_object()

        if not payment.external_payment_id:
            return Response(
                {"error": "Платёж ещё не создан в платёжной системе"},
                status=status.HTTP_400_BAD_REQUEST
            )

        yookassa = YooKassaService()
        payment_status = yookassa.get_payment_status(payment.external_payment_id)

        return Response(payment_status)


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
        return Payment.objects.filter(master=self.request.user.master_profile)


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
        wallet = request.user.master_profile.wallet
        destination = PayoutDestination.objects.get(id=data["destination_id"])

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
        ).select_related("client", "service").order_by("-date", "-end_time")

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
                "service_name": apt.service.name if apt.service else "Услуга",
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

        if settings.YOOKASSA_WEBHOOK_SECRET and signature:
            if not yookassa.verify_webhook_signature(request.body, signature):
                logger.warning("Invalid webhook signature")
                return Response(status=status.HTTP_401_UNAUTHORIZED)

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
