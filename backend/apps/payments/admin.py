"""
Admin configuration for payment models.
"""

from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RangeDateFilter
from unfold.decorators import display

from apps.payments.models import Payment, PayoutDestination, Wallet, Withdrawal


@admin.register(Wallet)
class WalletAdmin(ModelAdmin):
    list_display = [
        "master",
        "available_balance_display",
        "pending_balance_display",
        "hold_balance_display",
        "total_earned_display",
        "auto_withdraw_badge",
        "updated_at",
    ]
    list_filter = ["auto_withdraw", ("created_at", RangeDateFilter)]
    search_fields = ["master__user__email", "master__user__first_name", "master__user__last_name"]
    readonly_fields = [
        "available_balance",
        "pending_balance",
        "hold_balance",
        "total_earned",
        "total_withdrawn",
        "total_commission_paid",
        "created_at",
        "updated_at",
    ]
    list_filter_submit = True

    fieldsets = (
        ("Мастер", {
            "fields": ("master",)
        }),
        ("Балансы", {
            "fields": ("available_balance", "pending_balance", "hold_balance")
        }),
        ("Статистика", {
            "fields": ("total_earned", "total_withdrawn", "total_commission_paid")
        }),
        ("Настройки", {
            "fields": ("auto_withdraw",)
        }),
        ("Системная информация", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @display(description="Доступно")
    def available_balance_display(self, obj):
        return format_html('<span style="color: #22c55e; font-weight: bold;">{} ₽</span>', obj.available_balance)

    @display(description="В ожидании")
    def pending_balance_display(self, obj):
        return format_html('<span style="color: #f59e0b;">{} ₽</span>', obj.pending_balance)

    @display(description="Заморожено")
    def hold_balance_display(self, obj):
        return format_html('<span style="color: #ef4444;">{} ₽</span>', obj.hold_balance)

    @display(description="Всего заработано")
    def total_earned_display(self, obj):
        return f"{obj.total_earned} ₽"

    @display(description="Автовывод", boolean=True)
    def auto_withdraw_badge(self, obj):
        return obj.auto_withdraw


@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = [
        "id",
        "client",
        "master",
        "amount_display",
        "status_badge",
        "payment_type_display",
        "payment_method",
        "paid_at",
        "created_at",
    ]
    list_filter = ["status", "payment_type", "payment_method", "payment_provider", ("created_at", RangeDateFilter)]
    search_fields = [
        "id",
        "external_payment_id",
        "client__email",
        "master__user__email",
    ]
    readonly_fields = [
        "external_payment_id",
        "confirmation_url",
        "commission",
        "provider_fee",
        "net_amount",
        "refunded_amount",
        "paid_at",
        "available_at",
        "refunded_at",
        "payment_metadata",
        "created_at",
        "updated_at",
    ]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
    list_filter_submit = True
    list_per_page = 25

    fieldsets = (
        ("Основная информация", {
            "fields": ("appointment", "client", "master", "description")
        }),
        ("Платёж", {
            "fields": (
                "payment_type",
                "status",
                "payment_method",
                "payment_provider",
            )
        }),
        ("Суммы", {
            "fields": (
                "amount",
                "commission",
                "provider_fee",
                "net_amount",
                "refunded_amount",
            )
        }),
        ("Внешние данные", {
            "fields": (
                "external_payment_id",
                "confirmation_url",
                "payment_metadata",
            ),
            "classes": ("collapse",),
        }),
        ("Даты", {
            "fields": (
                "paid_at",
                "available_at",
                "refunded_at",
                "created_at",
                "updated_at",
            )
        }),
    )

    @display(description="Сумма")
    def amount_display(self, obj):
        return format_html('<strong>{} ₽</strong>', obj.amount)

    @display(
        description="Статус",
        label={
            "pending": "warning",
            "processing": "info",
            "succeeded": "success",
            "failed": "danger",
            "refunded": "secondary",
            "partially_refunded": "warning",
            "cancelled": "secondary",
        }
    )
    def status_badge(self, obj):
        return obj.status

    @display(description="Тип")
    def payment_type_display(self, obj):
        return obj.get_payment_type_display()


@admin.register(Withdrawal)
class WithdrawalAdmin(ModelAdmin):
    list_display = [
        "id",
        "wallet",
        "amount_display",
        "fee_display",
        "net_amount_display",
        "method_display",
        "status_badge",
        "created_at",
    ]
    list_filter = ["status", "method", ("created_at", RangeDateFilter)]
    search_fields = ["id", "wallet__master__user__email", "external_payout_id"]
    readonly_fields = [
        "fee",
        "net_amount",
        "external_payout_id",
        "processed_at",
        "completed_at",
        "created_at",
        "updated_at",
    ]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
    list_filter_submit = True
    list_per_page = 25

    actions = ["approve_withdrawals", "reject_withdrawals"]

    fieldsets = (
        ("Основная информация", {
            "fields": ("wallet", "destination", "method")
        }),
        ("Суммы", {
            "fields": ("amount", "fee", "net_amount")
        }),
        ("Статус", {
            "fields": ("status", "rejection_reason")
        }),
        ("Внешние данные", {
            "fields": ("external_payout_id",),
            "classes": ("collapse",),
        }),
        ("Даты", {
            "fields": ("processed_at", "completed_at", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @display(description="Сумма")
    def amount_display(self, obj):
        return format_html('<strong>{} ₽</strong>', obj.amount)

    @display(description="Комиссия")
    def fee_display(self, obj):
        return f"{obj.fee} ₽"

    @display(description="К выплате")
    def net_amount_display(self, obj):
        return format_html('<span style="color: #22c55e;">{} ₽</span>', obj.net_amount)

    @display(description="Способ")
    def method_display(self, obj):
        return obj.get_method_display()

    @display(
        description="Статус",
        label={
            "pending": "warning",
            "processing": "info",
            "completed": "success",
            "rejected": "danger",
            "failed": "danger",
        }
    )
    def status_badge(self, obj):
        return obj.status

    @admin.action(description="Одобрить выбранные запросы на вывод")
    def approve_withdrawals(self, request, queryset):
        from apps.payments.services import WithdrawalService

        service = WithdrawalService()
        count = 0
        for withdrawal in queryset.filter(status=Withdrawal.WithdrawalStatus.PENDING):
            try:
                destination = PayoutDestination.objects.filter(
                    master=withdrawal.wallet.master,
                    is_default=True
                ).first()
                if destination:
                    service.process_withdrawal(withdrawal, destination)
                    count += 1
            except Exception as e:
                self.message_user(request, f"Ошибка для {withdrawal.id}: {e}", level="error")

        self.message_user(request, f"Обработано запросов: {count}")

    @admin.action(description="Отклонить выбранные запросы на вывод")
    def reject_withdrawals(self, request, queryset):
        from apps.payments.services import WithdrawalService

        service = WithdrawalService()
        count = 0
        for withdrawal in queryset.filter(status=Withdrawal.WithdrawalStatus.PENDING):
            service.reject_withdrawal(withdrawal, "Отклонено администратором")
            count += 1

        self.message_user(request, f"Отклонено запросов: {count}")


@admin.register(PayoutDestination)
class PayoutDestinationAdmin(ModelAdmin):
    list_display = [
        "id",
        "master",
        "destination_type_display",
        "display_name",
        "is_default_badge",
        "is_verified_badge",
        "created_at",
    ]
    list_filter = ["destination_type", "is_default", "is_verified", ("created_at", RangeDateFilter)]
    search_fields = ["master__user__email", "card_last_four", "yoomoney_account"]
    readonly_fields = ["created_at", "updated_at"]
    list_filter_submit = True

    fieldsets = (
        ("Мастер", {
            "fields": ("master",)
        }),
        ("Реквизиты", {
            "fields": ("destination_type", "card_last_four", "yoomoney_account", "bank_name", "bik", "account_number")
        }),
        ("Настройки", {
            "fields": ("is_default", "is_verified")
        }),
        ("Системная информация", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @display(description="Тип")
    def destination_type_display(self, obj):
        return obj.get_destination_type_display()

    @display(description="Название")
    def display_name(self, obj):
        return str(obj)

    @display(description="По умолчанию", boolean=True)
    def is_default_badge(self, obj):
        return obj.is_default

    @display(description="Верифицирован", boolean=True)
    def is_verified_badge(self, obj):
        return obj.is_verified
