import logging

from django.core.cache import cache
from django.db.models import Q

logger = logging.getLogger(__name__)
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Chat, ChatMessage
from .serializers import (
    ChatCreateSerializer,
    ChatDetailSerializer,
    ChatMessageCreateSerializer,
    ChatMessageSerializer,
    ChatSerializer,
)

TYPING_TTL = 6  # seconds


@extend_schema_view(
    list=extend_schema(tags=["Чат"], summary="Список чатов"),
    retrieve=extend_schema(tags=["Чат"], summary="Детали чата"),
    create=extend_schema(tags=["Чат"], summary="Создать чат"),
)
class ChatViewSet(viewsets.ModelViewSet):
    """ViewSet for chats."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    http_method_names = ["get", "post"]

    def get_queryset(self):
        user = self.request.user
        role = self.request.query_params.get("role")

        if role == "client":
            return Chat.objects.filter(client=user).select_related(
                "master__user", "client"
            ).prefetch_related("messages")

        if role == "master" and hasattr(user, "master_profile"):
            return Chat.objects.filter(
                master=user.master_profile
            ).select_related("master__user", "client").prefetch_related("messages")

        if hasattr(user, "master_profile"):
            return Chat.objects.filter(
                Q(master=user.master_profile) | Q(client=user)
            ).select_related("master__user", "client").prefetch_related("messages")
        return Chat.objects.filter(client=user).select_related(
            "master__user", "client"
        ).prefetch_related("messages")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ChatDetailSerializer
        if self.action == "create":
            return ChatCreateSerializer
        return ChatSerializer

    @extend_schema(
        tags=["Чат"],
        summary="Отправить сообщение",
        request=ChatMessageCreateSerializer,
        responses={201: ChatMessageSerializer}
    )
    @action(detail=True, methods=["post"])
    def send_message(self, request, pk=None):
        """Send a message to the chat."""
        chat = self.get_object()
        user = request.user

        if hasattr(user, "master_profile") and chat.master == user.master_profile:
            sender_role = ChatMessage.SenderRole.MASTER
        elif chat.client == user:
            sender_role = ChatMessage.SenderRole.CLIENT
        else:
            return Response(
                {"detail": "Вы не являетесь участником этого чата"},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ChatMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        content = serializer.validated_data.get("content", "")
        file = serializer.validated_data.get("file") or request.FILES.get("file")
        reply_to_id = serializer.validated_data.get("reply_to_id")

        if file:
            # Validate file size (max 50MB)
            max_size = 50 * 1024 * 1024
            if file.size > max_size:
                return Response(
                    {"detail": "Файл слишком большой. Максимум 50 МБ"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if file.content_type and file.content_type.startswith("image/"):
                message_type = ChatMessage.MessageType.IMAGE
            elif file.content_type and file.content_type.startswith("audio/"):
                message_type = ChatMessage.MessageType.AUDIO
            else:
                message_type = ChatMessage.MessageType.FILE
        else:
            message_type = ChatMessage.MessageType.TEXT

        if not content and not file:
            return Response(
                {"detail": "Необходимо передать текст или файл"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Resolve reply_to
        reply_to = None
        if reply_to_id:
            try:
                reply_to = ChatMessage.objects.get(id=reply_to_id, chat=chat)
            except ChatMessage.DoesNotExist:
                pass

        message = ChatMessage.objects.create(
            chat=chat,
            sender=user,
            sender_role=sender_role,
            content=content,
            message_type=message_type,
            file=file,
            reply_to=reply_to,
        )

        chat.save(update_fields=["updated_at"])

        # Clear typing indicator after sending
        cache.delete(f"chat_typing:{chat.id}:{user.id}")

        try:
            from apps.core.notifications import NotificationService
            recipient = chat.client if sender_role == ChatMessage.SenderRole.MASTER else chat.master.user
            NotificationService.notify_chat_message(
                recipient_user=recipient,
                sender_name=user.full_name,
                message_preview=content or ("🎵 Голосовое" if message_type == ChatMessage.MessageType.AUDIO else "📎 Файл"),
                chat_id=str(chat.id)
            )
        except Exception:
            logger.exception("Notification failed for chat message")

        return Response(
            ChatMessageSerializer(message, context={"request": request}).data,
            status=status.HTTP_201_CREATED
        )

    @extend_schema(
        tags=["Чат"],
        summary="Получить сообщения чата",
        responses={200: ChatMessageSerializer(many=True)}
    )
    @action(detail=True, methods=["get"])
    def messages(self, request, pk=None):
        """Get messages with pagination and optional search."""
        chat = self.get_object()
        qs = chat.messages.select_related("sender", "reply_to", "reply_to__sender").order_by("-created_at")

        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(content__icontains=search)

        paginator = LimitOffsetPagination()
        paginator.default_limit = 40
        page = paginator.paginate_queryset(qs, request)
        serializer = ChatMessageSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(tags=["Чат"], summary="Отметить сообщения как прочитанные")
    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        """Mark all unread messages in chat as read."""
        chat = self.get_object()
        user = request.user

        if hasattr(user, "master_profile") and chat.master == user.master_profile:
            unread = chat.messages.filter(sender_role=ChatMessage.SenderRole.CLIENT, is_read=False)
        elif chat.client == user:
            unread = chat.messages.filter(sender_role=ChatMessage.SenderRole.MASTER, is_read=False)
        else:
            return Response(
                {"detail": "Вы не являетесь участником этого чата"},
                status=status.HTTP_403_FORBIDDEN
            )

        from django.utils import timezone
        count = unread.update(is_read=True, read_at=timezone.now())

        try:
            from apps.core.models import Notification
            Notification.objects.filter(
                user=user,
                notification_type=Notification.NotificationType.CHAT_MESSAGE,
                link__contains=str(chat.id),
                is_read=False
            ).update(is_read=True, read_at=timezone.now())
        except Exception:
            pass

        return Response({"marked_read": count})

    @extend_schema(tags=["Чат"], summary="Уведомить о наборе текста")
    @action(detail=True, methods=["post"])
    def typing(self, request, pk=None):
        """Set typing status for current user (TTL 6s)."""
        chat = self.get_object()
        user = request.user

        if not (
            (hasattr(user, "master_profile") and chat.master == user.master_profile)
            or chat.client == user
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        role = (
            "master"
            if hasattr(user, "master_profile") and chat.master == user.master_profile
            else "client"
        )
        cache.set(
            f"chat_typing:{chat.id}:{user.id}",
            {"role": role, "name": user.full_name},
            timeout=TYPING_TTL,
        )
        return Response({"status": "ok"})

    @extend_schema(tags=["Чат"], summary="Кто сейчас печатает")
    @action(detail=True, methods=["get"], url_path="who_is_typing")
    def who_is_typing(self, request, pk=None):
        """Return whether the other chat participant is currently typing."""
        chat = self.get_object()
        user = request.user

        # Determine the other participant's ID
        if hasattr(user, "master_profile") and chat.master == user.master_profile:
            other_id = chat.client_id
        else:
            other_id = chat.master.user_id

        data = cache.get(f"chat_typing:{chat.id}:{other_id}")
        return Response({"typing": data is not None})

    @extend_schema(
        tags=["Чат"],
        summary="Чат с мастером",
        description="Получить или создать чат с конкретным мастером"
    )
    @action(detail=False, methods=["get"], url_path="with-master/(?P<master_id>[^/.]+)")
    def with_master(self, request, master_id=None):
        """Get or create chat with a specific master."""
        from apps.users.models import MasterProfile

        try:
            master = MasterProfile.objects.get(id=master_id)
        except MasterProfile.DoesNotExist:
            return Response({"detail": "Мастер не найден"}, status=status.HTTP_404_NOT_FOUND)

        chat, created = Chat.objects.get_or_create(
            master=master,
            client=request.user,
            defaults={"is_active": True}
        )

        serializer = ChatDetailSerializer(chat, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
