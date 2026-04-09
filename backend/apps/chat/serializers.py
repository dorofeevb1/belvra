from rest_framework import serializers

from .models import Chat, ChatMessage


class ReplyMessageSerializer(serializers.ModelSerializer):
    """Minimal serializer for the replied-to message preview."""

    class Meta:
        model = ChatMessage
        fields = ["id", "content", "sender_role", "message_type"]


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for chat messages."""

    sender_name = serializers.SerializerMethodField()

    def get_sender_name(self, obj):
        if obj.sender:
            return obj.sender.full_name
        return "Удалённый пользователь"
    file_url = serializers.SerializerMethodField()
    reply_to = ReplyMessageSerializer(read_only=True)
    is_deleted = serializers.SerializerMethodField()
    forwarded_from_name = serializers.CharField(read_only=True)

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "chat",
            "sender",
            "sender_name",
            "sender_role",
            "content",
            "message_type",
            "file_url",
            "is_read",
            "reply_to",
            "is_deleted",
            "forwarded_from_name",
            "created_at",
        ]
        read_only_fields = ["id", "sender", "sender_name", "is_read", "created_at"]

    def get_is_deleted(self, obj):
        return obj.is_deleted_for_all

    def get_file_url(self, obj):
        if obj.is_deleted_for_all:
            return None
        if not obj.file:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # If deleted for all, mask content
        if instance.is_deleted_for_all:
            data["content"] = ""
            data["file_url"] = None
            data["message_type"] = "text"
        return data


class ChatMessageCreateSerializer(serializers.Serializer):
    """Serializer for creating chat messages."""

    content = serializers.CharField(required=False, allow_blank=True, default="")
    file = serializers.FileField(required=False, allow_null=True)
    reply_to_id = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, data):
        content = data.get("content", "").strip()
        file = data.get("file")
        if not content and not file:
            raise serializers.ValidationError("Необходимо передать текст или файл")
        return data


class ChatSerializer(serializers.ModelSerializer):
    """Serializer for chat list."""

    master_id = serializers.UUIDField(source="master.id", read_only=True)
    master_name = serializers.CharField(source="master.user.full_name", read_only=True)
    master_avatar = serializers.ImageField(source="master.user.avatar", read_only=True)
    master_is_online = serializers.BooleanField(source="master.user.is_online", read_only=True)
    master_last_seen = serializers.DateTimeField(source="master.user.last_seen", read_only=True)
    client_id = serializers.UUIDField(source="client.id", read_only=True)
    client_name = serializers.CharField(source="client.full_name", read_only=True)
    client_avatar = serializers.ImageField(source="client.avatar", read_only=True)
    client_is_online = serializers.BooleanField(source="client.is_online", read_only=True)
    client_last_seen = serializers.DateTimeField(source="client.last_seen", read_only=True)
    is_blocked = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    last_message_time = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = [
            "id",
            "master_id",
            "master_name",
            "master_avatar",
            "master_is_online",
            "master_last_seen",
            "client_id",
            "client_name",
            "client_avatar",
            "client_is_online",
            "client_last_seen",
            "is_blocked",
            "last_message",
            "last_message_time",
            "unread_count",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def get_is_blocked(self, obj):
        from apps.users.models import BlockedUser
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        user = request.user
        if hasattr(user, "master_profile") and obj.master == user.master_profile:
            other = obj.client
        else:
            other = obj.master.user
        return BlockedUser.objects.filter(blocker=user, blocked=other).exists()

    def get_last_message(self, obj):
        last_msg = obj.last_message
        if not last_msg:
            return None
        return last_msg.content or "📎 Файл"

    def get_last_message_time(self, obj):
        last_msg = obj.last_message
        return last_msg.created_at if last_msg else None

    def get_unread_count(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return 0
        user = request.user
        if hasattr(user, "master_profile") and obj.master == user.master_profile:
            return obj.unread_count_for_master
        return obj.unread_count_for_client


class ChatDetailSerializer(ChatSerializer):
    """Serializer for chat with messages."""

    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta(ChatSerializer.Meta):
        fields = ChatSerializer.Meta.fields + ["messages"]


class ChatCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a chat."""

    master_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Chat
        fields = ["master_id"]

    def validate_master_id(self, value):
        from apps.users.models import MasterProfile
        try:
            MasterProfile.objects.get(id=value)
        except MasterProfile.DoesNotExist:
            raise serializers.ValidationError("Мастер не найден")
        return value

    def create(self, validated_data):
        from apps.users.models import MasterProfile
        master = MasterProfile.objects.get(id=validated_data["master_id"])
        client = self.context["request"].user

        chat, created = Chat.objects.get_or_create(
            master=master,
            client=client,
            defaults={"is_active": True}
        )
        return chat
