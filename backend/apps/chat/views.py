from django.db.models import Q
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
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


@extend_schema_view(
    list=extend_schema(tags=["Чат"], summary="Список чатов"),
    retrieve=extend_schema(tags=["Чат"], summary="Детали чата"),
    create=extend_schema(tags=["Чат"], summary="Создать чат"),
)
class ChatViewSet(viewsets.ModelViewSet):
    """ViewSet for chats."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post"]

    def get_queryset(self):
        user = self.request.user
        # Show chats where user is either master or client
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

        # Determine sender role
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

        message = ChatMessage.objects.create(
            chat=chat,
            sender=user,
            sender_role=sender_role,
            content=serializer.validated_data["content"]
        )

        # Update chat timestamp
        chat.save(update_fields=["updated_at"])

        # Send notification to recipient
        try:
            from apps.core.notifications import NotificationService
            if sender_role == ChatMessage.SenderRole.MASTER:
                recipient = chat.client
            else:
                recipient = chat.master.user
            NotificationService.notify_chat_message(
                recipient_user=recipient,
                sender_name=user.full_name,
                message_preview=serializer.validated_data["content"],
                chat_id=str(chat.id)
            )
        except Exception:
            pass  # Don't fail message sending if notification fails

        return Response(
            ChatMessageSerializer(message).data,
            status=status.HTTP_201_CREATED
        )

    @extend_schema(
        tags=["Чат"],
        summary="Получить сообщения чата",
        responses={200: ChatMessageSerializer(many=True)}
    )
    @action(detail=True, methods=["get"])
    def messages(self, request, pk=None):
        """Get messages in a chat with pagination."""
        chat = self.get_object()
        messages = chat.messages.select_related("sender").order_by("-created_at")

        paginator = LimitOffsetPagination()
        paginator.default_limit = 50
        page = paginator.paginate_queryset(messages, request)
        serializer = ChatMessageSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        tags=["Чат"],
        summary="Отметить сообщения как прочитанные"
    )
    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        """Mark all unread messages in chat as read."""
        chat = self.get_object()
        user = request.user

        # Determine which messages to mark as read
        if hasattr(user, "master_profile") and chat.master == user.master_profile:
            # Master reads client messages
            unread = chat.messages.filter(
                sender_role=ChatMessage.SenderRole.CLIENT,
                is_read=False
            )
        elif chat.client == user:
            # Client reads master messages
            unread = chat.messages.filter(
                sender_role=ChatMessage.SenderRole.MASTER,
                is_read=False
            )
        else:
            return Response(
                {"detail": "Вы не являетесь участником этого чата"},
                status=status.HTTP_403_FORBIDDEN
            )

        from django.utils import timezone
        count = unread.update(is_read=True, read_at=timezone.now())

        return Response({"marked_read": count})

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
            return Response(
                {"detail": "Мастер не найден"},
                status=status.HTTP_404_NOT_FOUND
            )

        chat, created = Chat.objects.get_or_create(
            master=master,
            client=request.user,
            defaults={"is_active": True}
        )

        serializer = ChatDetailSerializer(chat, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
