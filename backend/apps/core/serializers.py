"""
Serializers for core models.
"""

from rest_framework import serializers

from .models import Notification


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
