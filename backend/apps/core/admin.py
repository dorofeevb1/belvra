from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RangeDateFilter
from unfold.decorators import display

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = [
        "title",
        "user",
        "notification_type_badge",
        "is_read_badge",
        "created_at"
    ]
    list_filter = [
        "notification_type",
        "is_read",
        ("created_at", RangeDateFilter)
    ]
    search_fields = ["title", "message", "user__email", "user__first_name"]
    ordering = ["-created_at"]
    list_filter_submit = True
    list_per_page = 50
    date_hierarchy = "created_at"

    readonly_fields = ["created_at", "updated_at", "read_at"]

    fieldsets = (
        (None, {
            "fields": ("user", "notification_type", "title", "message")
        }),
        ("Ссылка", {
            "fields": ("link",),
            "classes": ("collapse",)
        }),
        ("Статус", {
            "fields": ("is_read", "read_at")
        }),
        ("Даты", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    @display(
        description="Тип",
        label={
            "appointment_new": "info",
            "appointment_confirmed": "success",
            "appointment_cancelled": "danger",
            "appointment_rescheduled": "warning",
            "appointment_reminder": "info",
            "appointment_completed": "success",
            "review_new": "warning",
            "payment_received": "success",
            "payment_refunded": "danger",
            "system": "secondary"
        }
    )
    def notification_type_badge(self, obj):
        return obj.notification_type

    @display(description="Прочитано", boolean=True)
    def is_read_badge(self, obj):
        return obj.is_read

    actions = ["mark_as_read", "mark_as_unread"]

    @admin.action(description="Отметить как прочитанные")
    def mark_as_read(self, request, queryset):
        from django.utils import timezone
        count = queryset.filter(is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        self.message_user(request, f"Отмечено как прочитанные: {count}")

    @admin.action(description="Отметить как непрочитанные")
    def mark_as_unread(self, request, queryset):
        count = queryset.filter(is_read=True).update(
            is_read=False,
            read_at=None
        )
        self.message_user(request, f"Отмечено как непрочитанные: {count}")
