"""
Payment models for BeautyStyleService.
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import BaseModel


class Wallet(BaseModel):
    """Master wallet for storing earnings."""

    master = models.OneToOneField(
        "users.MasterProfile",
        on_delete=models.CASCADE,
        related_name="wallet"
    )
    available_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Доступный баланс"
    )
    pending_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="В ожидании (холд)"
    )
    hold_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Заморожено"
    )
    total_earned = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Всего заработано"
    )
    total_withdrawn = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Всего выведено"
    )
    total_commission_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Комиссия платформы"
    )
    auto_withdraw = models.BooleanField(
        default=False,
        verbose_name="Автовывод"
    )

    class Meta:
        verbose_name = "Кошелёк"
        verbose_name_plural = "Кошельки"

    def __str__(self):
        return f"Кошелёк {self.master.user.full_name}: {self.available_balance} ₽"

    @property
    def total_balance(self):
        """Total balance including pending."""
        return self.available_balance + self.pending_balance


class Payment(BaseModel):
    """Payment transaction model."""

    class PaymentType(models.TextChoices):
        PREPAYMENT = "prepayment", "Предоплата"
        FULL_PAYMENT = "full_payment", "Полная оплата"
        REMAINING = "remaining", "Доплата"
        TIP = "tip", "Чаевые"

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Ожидает оплаты"
        PROCESSING = "processing", "Обрабатывается"
        SUCCEEDED = "succeeded", "Успешно"
        FAILED = "failed", "Ошибка"
        REFUNDED = "refunded", "Возврат"
        PARTIALLY_REFUNDED = "partially_refunded", "Частичный возврат"
        CANCELLED = "cancelled", "Отменён"

    class PaymentMethod(models.TextChoices):
        CARD = "card", "Банковская карта"
        SBP = "sbp", "СБП"
        YOOMONEY = "yoomoney", "ЮMoney"
        CASH = "cash", "Наличные"

    class PaymentProvider(models.TextChoices):
        YOOKASSA = "yookassa", "YooKassa"
        TINKOFF = "tinkoff", "Тинькофф"
        SBERBANK = "sberbank", "Сбербанк"
        MANUAL = "manual", "Ручной ввод"

    # Relations
    appointment = models.ForeignKey(
        "appointments.Appointment",
        on_delete=models.CASCADE,
        related_name="payments",
        null=True,
        blank=True
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="client_payments"
    )
    master = models.ForeignKey(
        "users.MasterProfile",
        on_delete=models.CASCADE,
        related_name="master_payments"
    )

    # Payment info
    payment_type = models.CharField(
        max_length=20,
        choices=PaymentType.choices,
        default=PaymentType.FULL_PAYMENT
    )
    status = models.CharField(
        max_length=30,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        null=True,
        blank=True
    )
    payment_provider = models.CharField(
        max_length=20,
        choices=PaymentProvider.choices,
        default=PaymentProvider.YOOKASSA
    )

    # Amounts
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("1.00"))],
        verbose_name="Сумма платежа"
    )
    commission = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Комиссия платформы"
    )
    provider_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Комиссия провайдера"
    )
    net_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Сумма к выплате мастеру"
    )
    refunded_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Возвращённая сумма"
    )

    # External payment data
    external_payment_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        unique=True,
        db_index=True,
        verbose_name="ID платежа в платёжной системе"
    )
    confirmation_url = models.URLField(
        null=True,
        blank=True,
        verbose_name="Ссылка на оплату"
    )
    payment_metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Метаданные платежа"
    )

    # Timestamps
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата оплаты"
    )
    available_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата доступности средств"
    )
    refunded_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата возврата"
    )

    # Description
    description = models.TextField(
        blank=True,
        verbose_name="Описание"
    )

    class Meta:
        verbose_name = "Платёж"
        verbose_name_plural = "Платежи"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["client", "status"]),
            models.Index(fields=["master", "status"]),
        ]

    def __str__(self):
        return f"Платёж #{self.id} - {self.amount} ₽ ({self.get_status_display()})"

    def calculate_commission(self):
        """Calculate platform commission (5%)."""
        commission_rate = getattr(settings, "PLATFORM_COMMISSION_RATE", Decimal("0.05"))
        min_commission = getattr(settings, "MIN_COMMISSION", Decimal("10.00"))

        commission = self.amount * commission_rate
        self.commission = max(commission, min_commission)
        return self.commission

    def calculate_provider_fee(self):
        """Calculate payment provider fee (~2%)."""
        provider_fee_rate = getattr(settings, "PROVIDER_FEE_RATE", Decimal("0.02"))
        self.provider_fee = self.amount * provider_fee_rate
        return self.provider_fee

    def calculate_net_amount(self):
        """Calculate net amount for master."""
        if not self.commission:
            self.calculate_commission()
        if not self.provider_fee:
            self.calculate_provider_fee()

        self.net_amount = self.amount - self.commission - self.provider_fee
        return self.net_amount

    def save(self, *args, **kwargs):
        if not self.net_amount:
            self.calculate_net_amount()
        super().save(*args, **kwargs)


class Withdrawal(BaseModel):
    """Withdrawal request model."""

    class WithdrawalMethod(models.TextChoices):
        CARD = "card", "На карту"
        YOOMONEY = "yoomoney", "ЮMoney"
        BANK_ACCOUNT = "bank_account", "Расчётный счёт"

    class WithdrawalStatus(models.TextChoices):
        PENDING = "pending", "Ожидает обработки"
        PROCESSING = "processing", "Обрабатывается"
        COMPLETED = "completed", "Выполнен"
        REJECTED = "rejected", "Отклонён"
        FAILED = "failed", "Ошибка"

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="withdrawals"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("100.00"))],
        verbose_name="Сумма вывода"
    )
    fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Комиссия за вывод"
    )
    net_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Сумма к получению"
    )

    method = models.CharField(
        max_length=20,
        choices=WithdrawalMethod.choices
    )
    status = models.CharField(
        max_length=20,
        choices=WithdrawalStatus.choices,
        default=WithdrawalStatus.PENDING,
        db_index=True
    )

    # Destination details (encrypted in production)
    card_last_four = models.CharField(
        max_length=4,
        null=True,
        blank=True,
        verbose_name="Последние 4 цифры карты"
    )
    destination_account = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Счёт получателя"
    )

    # External data
    external_payout_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        unique=True,
        verbose_name="ID выплаты в платёжной системе"
    )

    # Timestamps
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата обработки"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата завершения"
    )

    rejection_reason = models.TextField(
        blank=True,
        verbose_name="Причина отклонения"
    )

    class Meta:
        verbose_name = "Запрос на вывод"
        verbose_name_plural = "Запросы на вывод"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["wallet", "status"]),
        ]

    def __str__(self):
        return f"Вывод #{self.id} - {self.amount} ₽ ({self.get_status_display()})"

    def calculate_fee(self):
        """Calculate withdrawal fee based on method."""
        withdrawal_fees = getattr(settings, "WITHDRAWAL_FEES", {
            "card": {"fixed": Decimal("50.00"), "percent": Decimal("0.00")},
            "yoomoney": {"fixed": Decimal("0.00"), "percent": Decimal("0.03")},
            "bank_account": {"fixed": Decimal("0.00"), "percent": Decimal("0.01")},
        })

        fees = withdrawal_fees.get(self.method, {"fixed": Decimal("0.00"), "percent": Decimal("0.00")})
        self.fee = fees["fixed"] + (self.amount * fees["percent"])
        self.net_amount = self.amount - self.fee
        return self.fee

    def save(self, *args, **kwargs):
        if not self.net_amount:
            self.calculate_fee()
        super().save(*args, **kwargs)


class PayoutDestination(BaseModel):
    """Saved payout destination for master."""

    class DestinationType(models.TextChoices):
        CARD = "card", "Банковская карта"
        YOOMONEY = "yoomoney", "ЮMoney"
        BANK_ACCOUNT = "bank_account", "Расчётный счёт"

    master = models.ForeignKey(
        "users.MasterProfile",
        on_delete=models.CASCADE,
        related_name="payout_destinations"
    )
    destination_type = models.CharField(
        max_length=20,
        choices=DestinationType.choices
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name="По умолчанию"
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Верифицирован"
    )

    # Card details (last 4 digits only for display)
    card_last_four = models.CharField(
        max_length=4,
        null=True,
        blank=True
    )
    card_type = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Тип карты (Visa, MC, МИР)"
    )

    # YooMoney
    yoomoney_account = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Счёт ЮMoney"
    )

    # Bank account
    bank_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Название банка"
    )
    bik = models.CharField(
        max_length=9,
        null=True,
        blank=True,
        verbose_name="БИК"
    )
    account_number = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Номер счёта"
    )

    # Token for secure payout (stored encrypted)
    payout_token = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Токен для выплаты"
    )

    class Meta:
        verbose_name = "Способ вывода"
        verbose_name_plural = "Способы вывода"
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        if self.destination_type == self.DestinationType.CARD:
            return f"Карта **** {self.card_last_four}"
        elif self.destination_type == self.DestinationType.YOOMONEY:
            return f"ЮMoney {self.yoomoney_account}"
        else:
            return f"{self.bank_name} **** {self.account_number[-4:] if self.account_number else '****'}"

    def save(self, *args, **kwargs):
        # Ensure only one default destination per master
        if self.is_default:
            PayoutDestination.objects.filter(
                master=self.master,
                is_default=True
            ).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)
