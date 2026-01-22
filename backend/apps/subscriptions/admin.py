"""
Admin configuration for subscription models.
"""

from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Subscription, SubscriptionPayment, SubscriptionPlan


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(ModelAdmin):
    list_display = [
        "name", "tier", "user_type", "period", "price",
        "commission_percent", "is_active"
    ]
    list_filter = ["tier", "user_type", "period", "is_active"]
    search_fields = ["name"]
    ordering = ["user_type", "tier", "period"]


@admin.register(Subscription)
class SubscriptionAdmin(ModelAdmin):
    list_display = [
        "user", "plan", "status", "current_period_start",
        "current_period_end", "auto_renew", "created_at"
    ]
    list_filter = ["status", "auto_renew", "plan__tier"]
    search_fields = ["user__email", "user__first_name", "user__last_name"]
    raw_id_fields = ["user", "plan"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]


@admin.register(SubscriptionPayment)
class SubscriptionPaymentAdmin(ModelAdmin):
    list_display = [
        "id", "subscription", "amount", "currency", "status",
        "is_recurring", "paid_at", "created_at"
    ]
    list_filter = ["status", "is_recurring", "currency"]
    search_fields = ["subscription__user__email", "external_payment_id"]
    raw_id_fields = ["subscription"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]
