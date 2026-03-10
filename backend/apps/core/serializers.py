"""
Serializers for core models.
"""

from rest_framework import serializers

from .models import Notification, DeviceToken


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model."""

    notification_type_display = serializers.CharField(
        source="get_notification_type_display",
        read_only=True
    )

    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "notification_type_display",
            "title",
            "message",
            "link",
            "is_read",
            "read_at",
            "created_at"
        ]
        read_only_fields = ["id", "created_at", "read_at"]


class NotificationMarkReadSerializer(serializers.Serializer):
    """Serializer for marking notifications as read."""

    notification_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="List of notification IDs to mark as read. If empty, marks all as read."
    )


class DeviceTokenSerializer(serializers.ModelSerializer):
    """Serializer for DeviceToken model."""

    class Meta:
        model = DeviceToken
        fields = [
            "id",
            "token",
            "platform",
            "device_name",
            "is_active",
            "last_used_at",
            "created_at"
        ]
        read_only_fields = ["id", "last_used_at", "created_at"]

    def create(self, validated_data):
        """Create or update device token."""
        user = self.context["request"].user
        token = validated_data.get("token")

        # Delete any existing token for OTHER users (device switched accounts)
        DeviceToken.objects.filter(token=token).exclude(user=user).delete()

        # Update existing token or create new one for this user
        device_token, created = DeviceToken.objects.update_or_create(
            token=token,
            user=user,
            defaults={
                "platform": validated_data.get("platform", "android"),
                "device_name": validated_data.get("device_name", ""),
                "is_active": validated_data.get("is_active", True),
            }
        )
        return device_token
