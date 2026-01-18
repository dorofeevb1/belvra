from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from .models import Chat, ChatMessage


class ChatMessageInline(TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ["sender", "sender_role", "content", "is_read", "created_at"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Chat)
class ChatAdmin(ModelAdmin):
    list_display = ["id", "master_name", "client_name", "messages_count", "is_active_badge", "updated_at"]
    list_filter = ["is_active"]
    search_fields = ["master__user__email", "client__email", "master__user__first_name", "client__first_name"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [ChatMessageInline]
    list_filter_submit = True

    @display(description="Мастер")
    def master_name(self, obj):
        return obj.master.user.full_name

    @display(description="Клиент")
    def client_name(self, obj):
        return obj.client.full_name

    @display(description="Сообщений")
    def messages_count(self, obj):
        return obj.messages.count()

    @display(description="Активен", boolean=True)
    def is_active_badge(self, obj):
        return obj.is_active


@admin.register(ChatMessage)
class ChatMessageAdmin(ModelAdmin):
    list_display = ["short_content", "chat", "sender_name", "sender_role", "is_read_badge", "created_at"]
    list_filter = ["sender_role", "is_read"]
    search_fields = ["content", "sender__email"]
    readonly_fields = ["chat", "sender", "sender_role", "content", "is_read", "read_at", "created_at"]
    list_filter_submit = True
    list_per_page = 50

    @display(description="Сообщение")
    def short_content(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content

    @display(description="Отправитель")
    def sender_name(self, obj):
        return obj.sender.full_name

    @display(description="Прочитано", boolean=True)
    def is_read_badge(self, obj):
        return obj.is_read
