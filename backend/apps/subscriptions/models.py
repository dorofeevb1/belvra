"""
Subscription models for managing user subscriptions.
"""

import uuid

from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel
from apps.users.models import User


class SubscriptionPlan(BaseModel):
    """Subscription plan model defining available plans."""

    class Tier(models.TextChoices):
        FREE = "free", "Бесплатный"
        PRO = "pro", "Pro"

    class UserType(models.TextChoices):
        MASTER = "master", "Мастер"
        CLIENT = "client", "Клиент"

    class Period(models.TextChoices):
        MONTHLY = "monthly", "Месяц"
        YEARLY = "yearly", "Год"

    class AnalyticsLevel(models.TextChoices):
        NONE = "none", "Нет"
        BASIC = "basic", "Базовая"
        ADVANCED = "advanced", "Расширенная"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name="Название")
    tier = models.CharField(max_length=20, choices=Tier.choices, default=Tier.FREE)
    user_type = models.CharField(max_length=20, choices=UserType.choices)
    period = models.CharField(max_length=20, choices=Period.choices, default=Period.MONTHLY)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # Master limits
    max_appointments_per_month = models.PositiveIntegerField(
        default=0,
        help_text="0 = unlimited"
    )
    max_services_count = models.PositiveIntegerField(
        default=0,
        help_text="0 = unlimited"
    )
    max_portfolio_items = models.PositiveIntegerField(
        default=0,
        help_text="0 = unlimited"
    )
    commission_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=5.00,
        help_text="Platform commission percentage"
    )
    search_boost_enabled = models.BooleanField(default=False)
    analytics_level = models.CharField(
        max_length=20,
        choices=AnalyticsLevel.choices,
        default=AnalyticsLevel.NONE
    )

    # Client benefits
    priority_booking = models.BooleanField(default=False)
    cashback_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Feature flags
    ai_assistant_enabled = models.BooleanField(default=False)
    advanced_notifications = models.BooleanField(default=False)
    export_data_enabled = models.BooleanField(default=False)

    # Client PRO features
    extended_search = models.BooleanField(
        default=False, help_text="Расширенные фильтры поиска мастеров"
    )
    history_months = models.PositiveIntegerField(
        default=3, help_text="Кол-во месяцев истории записей (0 = без ограничений)"
    )
    client_stats_enabled = models.BooleanField(
        default=False, help_text="Доступ к статистике расходов"
    )
    max_favorites = models.PositiveIntegerField(
        default=5, help_text="Макс. избранных мастеров (0 = без ограничений)"
    )

    # Master PRO features
    pro_badge = models.BooleanField(
        default=False, help_text="Бейдж PRO в профиле мастера"
    )
    client_notes_enabled = models.BooleanField(
        default=False, help_text="Заметки о клиентах (мини-CRM)"
    )
    max_pinned_portfolio = models.PositiveIntegerField(
        default=0, help_text="Макс. закреплённых работ в портфолио (0 = нельзя)"
    )
    rebooking_reminder_enabled = models.BooleanField(
        default=False, help_text="Автоматические напоминания клиентам о повторной записи"
    )

    class Meta:
        verbose_name = "План подписки"
        verbose_name_plural = "Планы подписок"
        ordering = ["user_type", "tier", "period"]
        unique_together = ["tier", "user_type", "period"]

    def __str__(self):
        return f"{self.name} ({self.get_user_type_display()} - {self.get_period_display()})"

    @property
    def is_free(self):
        return self.tier == self.Tier.FREE

    @property
    def is_pro(self):
        return self.tier == self.Tier.PRO


class Subscription(BaseModel):
    """User subscription model."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Активна"
        CANCELLED = "cancelled", "Отменена"
        EXPIRED = "expired", "Истекла"
        PENDING = "pending", "Ожидает оплаты"
        PAST_DUE = "past_due", "Просрочена"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="subscription"
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    auto_renew = models.BooleanField(default=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    # T-Bank RebillId for recurring payments
    tbank_rebill_id = models.CharField(max_length=255, blank=True)

    # Usage tracking
    appointments_this_month = models.PositiveIntegerField(default=0)
    last_usage_reset = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.plan.name}"

    @property
    def is_active(self):
        if self.status != self.Status.ACTIVE:
            return False
        if self.current_period_end and self.current_period_end < timezone.now():
            return False
        return True

    @property
    def days_until_expiry(self):
        if not self.current_period_end:
            return None
        delta = self.current_period_end - timezone.now()
        return max(0, delta.days)

    def reset_monthly_usage(self):
        """Reset monthly usage counters."""
        self.appointments_this_month = 0
        self.last_usage_reset = timezone.now().date()
        self.save(update_fields=["appointments_this_month", "last_usage_reset"])

    def can_create_appointment(self):
        """Check if user can create more appointments this month."""
        limit = self.plan.max_appointments_per_month
        if limit == 0:  # Unlimited
            return True
        return self.appointments_this_month < limit

    def can_add_service(self, current_count):
        """Check if master can add more services."""
        limit = self.plan.max_services_count
        if limit == 0:  # Unlimited
            return True
        return current_count < limit

    def can_add_portfolio_item(self, current_count):
        """Check if master can add more portfolio items."""
        limit = self.plan.max_portfolio_items
        if limit == 0:  # Unlimited
            return True
        return current_count < limit


class Referral(BaseModel):
    """Tracks referral rewards."""

    class RewardType(models.TextChoices):
        FREE_MONTH_PRO = "free_month_pro", "Бесплатный месяц Pro"

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает"
        APPLIED = "applied", "Применено"
        EXPIRED = "expired", "Истекло"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    referrer = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="referral_rewards",
        verbose_name="Пригласивший"
    )
    referred_user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="referral_source",
        verbose_name="Приглашённый"
    )
    reward_type = models.CharField(
        max_length=30, choices=RewardType.choices,
        default=RewardType.FREE_MONTH_PRO
    )
    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.PENDING
    )
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Реферал"
        verbose_name_plural = "Рефералы"
        unique_together = ["referrer", "referred_user"]
        ordering = ["-created_at"]
        constraints = []

    def __str__(self):
        return f"{self.referrer.email} -> {self.referred_user.email}"


class SubscriptionPayment(BaseModel):
    """Payment record for subscriptions."""

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает"
        SUCCEEDED = "succeeded", "Успешно"
        FAILED = "failed", "Неудачно"
        CANCELLED = "cancelled", "Отменено"
        REFUNDED = "refunded", "Возвращено"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="payments"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="RUB")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    external_payment_id = models.CharField(max_length=255, blank=True, db_index=True)
    confirmation_url = models.URLField(max_length=500, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    is_recurring = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        verbose_name = "Платёж за подписку"
        verbose_name_plural = "Платежи за подписки"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment {self.id} - {self.subscription.user.email} - {self.amount} {self.currency}"


