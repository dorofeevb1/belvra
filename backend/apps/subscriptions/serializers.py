"""
Serializers for subscription management.
"""

from rest_framework import serializers

from .models import Subscription, SubscriptionPayment, SubscriptionPlan


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Serializer for subscription plans."""

    is_free = serializers.ReadOnlyField()
    is_pro = serializers.ReadOnlyField()
    discount_percentage = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionPlan
        fields = [
            "id", "name", "tier", "user_type", "period",
            "price", "original_price", "is_active",
            "max_appointments_per_month", "max_services_count",
            "max_portfolio_items", "commission_percent",
            "search_boost_enabled", "analytics_level",
            "priority_booking", "cashback_percent", "discount_percent",
            "ai_assistant_enabled", "advanced_notifications", "export_data_enabled",
            "is_free", "is_pro", "discount_percentage"
        ]
        read_only_fields = ["id"]

    def get_discount_percentage(self, obj):
        if obj.original_price and obj.original_price > obj.price:
            discount = ((obj.original_price - obj.price) / obj.original_price) * 100
            return round(discount, 0)
        return None


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for user subscription."""

    plan = SubscriptionPlanSerializer(read_only=True)
    is_active = serializers.ReadOnlyField()
    days_until_expiry = serializers.ReadOnlyField()

    class Meta:
        model = Subscription
        fields = [
            "id", "plan", "status", "current_period_start",
            "current_period_end", "cancel_at_period_end", "auto_renew",
            "cancelled_at", "appointments_this_month", "is_active",
            "days_until_expiry", "created_at"
        ]
        read_only_fields = ["id", "created_at"]


class SubscriptionUsageSerializer(serializers.Serializer):
    """Serializer for subscription usage statistics."""

    appointments_used = serializers.IntegerField()
    appointments_limit = serializers.IntegerField()
    appointments_remaining = serializers.IntegerField()
    services_count = serializers.IntegerField()
    services_limit = serializers.IntegerField()
    services_remaining = serializers.IntegerField()
    portfolio_items_count = serializers.IntegerField()
    portfolio_items_limit = serializers.IntegerField()
    portfolio_items_remaining = serializers.IntegerField()
    plan_tier = serializers.CharField()
    plan_name = serializers.CharField()


class SubscribeRequestSerializer(serializers.Serializer):
    """Serializer for subscription request."""

    plan_id = serializers.UUIDField()
    payment_method = serializers.CharField(required=False, allow_blank=True)
    return_url = serializers.URLField(required=False)
    save_payment_method = serializers.BooleanField(default=True)


class SubscribeResponseSerializer(serializers.Serializer):
    """Serializer for subscription response."""

    subscription_id = serializers.UUIDField()
    payment_url = serializers.URLField(allow_null=True)
    status = serializers.CharField()
    message = serializers.CharField()


class CancelSubscriptionSerializer(serializers.Serializer):
    """Serializer for subscription cancellation."""

    immediately = serializers.BooleanField(default=False)
    reason = serializers.CharField(required=False, allow_blank=True)


class ChangePlanSerializer(serializers.Serializer):
    """Serializer for changing subscription plan."""

    plan_id = serializers.UUIDField()
    immediately = serializers.BooleanField(default=False)


class SubscriptionPaymentSerializer(serializers.ModelSerializer):
    """Serializer for subscription payments."""

    class Meta:
        model = SubscriptionPayment
        fields = [
            "id", "amount", "currency", "status",
            "payment_method", "is_recurring", "paid_at",
            "created_at"
        ]
        read_only_fields = ["id", "created_at"]


class CheckLimitSerializer(serializers.Serializer):
    """Serializer for limit check response."""

    allowed = serializers.BooleanField()
    current = serializers.IntegerField()
    limit = serializers.IntegerField()
    remaining = serializers.IntegerField()
    message = serializers.CharField(required=False)
