import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.chat_id = self.scope["url_route"]["kwargs"]["chat_id"]
        self.room_group = f"chat_{self.chat_id}"
        self.user = self.scope["user"]

        if self.user.is_anonymous:
            await self.close()
            return

        is_participant = await self.check_participant()
        if not is_participant:
            await self.close()
            return

        self.last_message_time = 0
        self.message_count = 0
        self.window_start = 0

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_group"):
            await self.channel_layer.group_discard(self.room_group, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        msg_type = data.get("type")

        if msg_type == "chat_message":
            import time
            now = time.time()
            if now - self.window_start > 3:
                self.window_start = now
                self.message_count = 0
            self.message_count += 1
            if self.message_count > 5:
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "Слишком много сообщений. Подождите.",
                }))
                return

            content = data.get("content", "").strip()
            if not content:
                return
            message = await self.save_message(content)
            await self.channel_layer.group_send(
                self.room_group,
                {"type": "chat.message", "message": message},
            )
        elif msg_type == "typing":
            await self.channel_layer.group_send(
                self.room_group,
                {
                    "type": "chat.typing",
                    "user_id": str(self.user.id),
                },
            )
        elif msg_type == "read":
            count = await self.mark_messages_read()
            await self.channel_layer.group_send(
                self.room_group,
                {"type": "chat.read", "user_id": str(self.user.id), "count": count},
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["message"]))

    async def chat_typing(self, event):
        if event["user_id"] != str(self.user.id):
            await self.send(text_data=json.dumps({
                "type": "typing",
                "user_id": event["user_id"],
            }))

    async def chat_read(self, event):
        await self.send(text_data=json.dumps({
            "type": "read",
            "user_id": event["user_id"],
            "count": event.get("count", 0),
        }))

    @database_sync_to_async
    def check_participant(self):
        from apps.chat.models import Chat
        return Chat.objects.filter(
            Q(id=self.chat_id),
            Q(client=self.user) | Q(master__user=self.user),
        ).exists()

    @database_sync_to_async
    def save_message(self, content):
        from apps.chat.models import Chat, ChatMessage
        chat = Chat.objects.select_related("master__user").get(id=self.chat_id)
        is_master = hasattr(self.user, "master_profile") and chat.master == self.user.master_profile
        sender_role = "master" if is_master else "client"
        msg = ChatMessage.objects.create(
            chat=chat,
            sender=self.user,
            sender_role=sender_role,
            content=content,
            message_type="text",
        )
        return {
            "type": "message",
            "id": str(msg.id),
            "chat_id": str(chat.id),
            "sender_id": str(self.user.id),
            "sender_role": sender_role,
            "content": content,
            "message_type": "text",
            "created_at": msg.created_at.isoformat(),
        }

    @database_sync_to_async
    def mark_messages_read(self):
        from apps.chat.models import ChatMessage
        return ChatMessage.objects.filter(
            chat_id=self.chat_id,
            is_read=False,
        ).exclude(
            sender=self.user,
        ).update(is_read=True, read_at=timezone.now())
