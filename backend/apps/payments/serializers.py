"""
Serializers for payment API.
"""

from decimal import Decimal

from django.conf import settings
from rest_framework import serializers

from apps.appointments.models import Appointment
from apps.payments.models import Payment, PayoutDestination, Wallet, Withdrawal


class WalletSerializer(serializers.ModelSerializer):
    """Serializer for master wallet."""

    master_name = serializers.CharField(source="master.user.full_name", read_only=True)
    total_balance = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = Wallet
        fields = [
            "id",
            "master_name",
            "available_balance",
            "pending_balance",
            "hold_balance",
            "total_balance",
            "total_earned",
            "total_withdrawn",
            "total_commission_paid",
            "auto_withdraw",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "available_balance",
            "pending_balance",
            "hold_balance",
            "total_earned",
            "total_withdrawn",
            "total_commission_paid",
            "updated_at",
        ]


class WalletStatsSerializer(serializers.Serializer):
    """Serializer for wallet statistics."""

    period = serializers.CharField()
    total_earnings = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_payments = serializers.IntegerField()
    average_payment = serializers.DecimalField(max_digits=12, decimal_places=2)
    commission_paid = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_earnings = serializers.DecimalField(max_digits=12, decimal_places=2)


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payment."""

    client_name = serializers.CharField(source="client.full_name", read_only=True)
    master_name = serializers.CharField(source="master.user.full_name", read_only=True)
    service_name = serializers.CharField(source="appointment.service.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    payment_type_display = serializers.CharField(source="get_payment_type_display", read_only=True)
    payment_method_display = serializers.CharField(source="get_payment_method_display", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "appointment",
            "client",
            "client_name",
            "master",
            "master_name",
            "service_name",
            "payment_type",
            "payment_type_display",
            "status",
            "status_display",
            "payment_method",
            "payment_method_display",
            "payment_provider",
            "amount",
            "commission",
            "provider_fee",
            "net_amount",
            "refunded_amount",
            "external_payment_id",
            "confirmation_url",
            "description",
            "paid_at",
            "available_at",
            "refunded_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "client",
            "master",
            "status",
            "commission",
            "provider_fee",
            "net_amount",
            "refunded_amount",
            "external_payment_id",
            "confirmation_url",
            "paid_at",
            "available_at",
            "refunded_at",
            "created_at",
        ]


class CreatePaymentSerializer(serializers.Serializer):
    """Serializer for creating a new payment."""

    PAYMENT_METHOD_CHOICES = [
        ("bank_card", "Банковская карта"),
        ("sbp", "СБП"),
        ("yoo_money", "ЮMoney"),
    ]

    appointment_id = serializers.UUIDField()
    payment_type = serializers.ChoiceField(
        choices=Payment.PaymentType.choices,
        default=Payment.PaymentType.FULL_PAYMENT
    )
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        min_value=Decimal("1.00")
    )
    return_url = serializers.URLField(required=False)
    payment_method = serializers.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES,
        required=False,
        help_text="Предпочтительный способ оплаты: bank_card или sbp"
    )

    def validate_appointment_id(self, value):
        try:
            appointment = Appointment.objects.get(id=value)
        except Appointment.DoesNotExist:
            raise serializers.ValidationError("Запись не найдена")

        # Check if user is the client of this appointment
        request = self.context.get("request")
        if request and appointment.client != request.user:
            raise serializers.ValidationError("Вы не являетесь клиентом этой записи")

        # Check appointment status
        if appointment.status not in [Appointment.Status.PENDING, Appointment.Status.CONFIRMED]:
            raise serializers.ValidationError("Оплата невозможна для этой записи")

        return value


class RefundSerializer(serializers.Serializer):
    """Serializer for refund request."""

    payment_id = serializers.UUIDField()
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        min_value=Decimal("1.00")
    )
    reason = serializers.CharField(max_length=500, required=False, default="")

    def validate_payment_id(self, value):
        try:
            payment = Payment.objects.get(id=value)
        except Payment.DoesNotExist:
            raise serializers.ValidationError("Платёж не найден")

        if payment.status not in [Payment.PaymentStatus.SUCCEEDED, Payment.PaymentStatus.PARTIALLY_REFUNDED]:
            raise serializers.ValidationError("Возврат невозможен для этого платежа")

        return value

    def validate(self, data):
        payment_id = data.get("payment_id")
        amount = data.get("amount")

        if amount:
            payment = Payment.objects.get(id=payment_id)
            max_refund = payment.amount - payment.refunded_amount
            if amount > max_refund:
                raise serializers.ValidationError({
                    "amount": f"Максимальная сумма возврата: {max_refund} ₽"
                })

        return data


class PayoutDestinationSerializer(serializers.ModelSerializer):
    """Serializer for payout destination."""

    destination_type_display = serializers.CharField(
        source="get_destination_type_display",
        read_only=True
    )
    display_name = serializers.CharField(source="__str__", read_only=True)

    class Meta:
        model = PayoutDestination
        fields = [
            "id",
            "destination_type",
            "destination_type_display",
            "display_name",
            "is_default",
            "is_verified",
            "card_last_four",
            "card_type",
            "yoomoney_account",
            "bank_name",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "is_verified",
            "card_last_four",
            "card_type",
            "created_at",
        ]


class CreatePayoutDestinationSerializer(serializers.Serializer):
    """Serializer for creating a payout destination."""

    destination_type = serializers.ChoiceField(choices=PayoutDestination.DestinationType.choices)
    is_default = serializers.BooleanField(default=False)

    # Card fields
    card_number = serializers.CharField(max_length=19, required=False)

    # YooMoney fields
    yoomoney_account = serializers.CharField(max_length=50, required=False)

    # Bank account fields
    bank_name = serializers.CharField(max_length=100, required=False)
    bik = serializers.CharField(max_length=9, required=False)
    account_number = serializers.CharField(max_length=20, required=False)

    def validate(self, data):
        dest_type = data.get("destination_type")

        if dest_type == PayoutDestination.DestinationType.CARD:
            if not data.get("card_number"):
                raise serializers.ValidationError({"card_number": "Необходимо указать номер карты"})
            # Validate card number (Luhn algorithm would be here in production)
            card_number = data["card_number"].replace(" ", "")
            if not card_number.isdigit() or len(card_number) < 16:
                raise serializers.ValidationError({"card_number": "Некорректный номер карты"})

        elif dest_type == PayoutDestination.DestinationType.YOOMONEY:
            if not data.get("yoomoney_account"):
                raise serializers.ValidationError({"yoomoney_account": "Необходимо указать номер кошелька"})

        elif dest_type == PayoutDestination.DestinationType.BANK_ACCOUNT:
            if not data.get("bik"):
                raise serializers.ValidationError({"bik": "Необходимо указать БИК"})
            if not data.get("account_number"):
                raise serializers.ValidationError({"account_number": "Необходимо указать номер счёта"})

        return data


class WithdrawalSerializer(serializers.ModelSerializer):
    """Serializer for withdrawal."""

    method_display = serializers.CharField(source="get_method_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Withdrawal
        fields = [
            "id",
            "amount",
            "fee",
            "net_amount",
            "method",
            "method_display",
            "status",
            "status_display",
            "card_last_four",
            "destination_account",
            "processed_at",
            "completed_at",
            "rejection_reason",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "fee",
            "net_amount",
            "status",
            "card_last_four",
            "destination_account",
            "processed_at",
            "completed_at",
            "rejection_reason",
            "created_at",
        ]


class CreateWithdrawalSerializer(serializers.Serializer):
    """Serializer for creating a withdrawal request."""

    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("100.00")
    )
    destination_id = serializers.UUIDField()

    def validate_destination_id(self, value):
        request = self.context.get("request")
        try:
            destination = PayoutDestination.objects.get(
                id=value,
                master=request.user.master_profile
            )
        except PayoutDestination.DoesNotExist:
            raise serializers.ValidationError("Способ вывода не найден")

        if not destination.is_verified:
            raise serializers.ValidationError("Способ вывода не верифицирован")

        return value

    def validate_amount(self, value):
        request = self.context.get("request")
        try:
            wallet = request.user.master_profile.wallet
        except Wallet.DoesNotExist:
            raise serializers.ValidationError("Кошелёк не найден")

        if value > wallet.available_balance:
            raise serializers.ValidationError(
                f"Недостаточно средств. Доступно: {wallet.available_balance} ₽"
            )

        min_withdrawal = getattr(settings, "MIN_WITHDRAWAL_AMOUNT", Decimal("100.00"))
        if value < min_withdrawal:
            raise serializers.ValidationError(f"Минимальная сумма вывода: {min_withdrawal} ₽")

        return value


class WebhookPaymentSerializer(serializers.Serializer):
    """Serializer for YooKassa webhook payload."""

    type = serializers.CharField()
    event = serializers.CharField()
    object = serializers.DictField()

    def validate_type(self, value):
        if value != "notification":
            raise serializers.ValidationError("Invalid notification type")
        return value

    def validate_event(self, value):
        valid_events = [
            "payment.succeeded",
            "payment.canceled",
            "payment.waiting_for_capture",
            "refund.succeeded",
            "payout.succeeded",
            "payout.canceled",
        ]
        if value not in valid_events:
            raise serializers.ValidationError(f"Unsupported event: {value}")
        return value
