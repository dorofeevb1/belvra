from rest_framework import serializers

from .models import TodoItem


class TodoItemSerializer(serializers.ModelSerializer):
    """Serializer for todo items."""

    master_id = serializers.UUIDField(source="master.id", read_only=True)

    class Meta:
        model = TodoItem
        fields = [
            "id",
            "master_id",
            "title",
            "description",
            "date",
            "time",
            "status",
            "priority",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "master_id", "created_at", "updated_at"]


class TodoItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating todo items."""

    master_id = serializers.UUIDField(source="master.id", read_only=True)

    class Meta:
        model = TodoItem
        fields = [
            "id",
            "master_id",
            "title",
            "description",
            "date",
            "time",
            "status",
            "priority",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "master_id", "created_at", "updated_at"]


class TodoItemStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating todo status."""

    status = serializers.ChoiceField(choices=TodoItem.Status.choices)
