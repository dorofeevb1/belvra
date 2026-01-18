from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RangeDateFilter
from unfold.decorators import display

from .models import Appointment, Review, WorkSchedule


WEEKDAY_NAMES = {
    0: "Понедельник",
    1: "Вторник",
    2: "Среда",
    3: "Четверг",
    4: "Пятница",
    5: "Суббота",
    6: "Воскресенье",
}


@admin.register(WorkSchedule)
class WorkScheduleAdmin(ModelAdmin):
    list_display = ["master", "weekday_display", "time_range", "is_working_badge"]
    list_filter = ["weekday", "is_working"]
    search_fields = ["master__user__email"]
    list_filter_submit = True
    ordering = ["master", "weekday"]

    @display(description="День недели")
    def weekday_display(self, obj):
        return WEEKDAY_NAMES.get(obj.weekday, obj.weekday)

    @display(description="Время работы")
    def time_range(self, obj):
        if obj.start_time and obj.end_time:
            return f"{obj.start_time.strftime('%H:%M')} — {obj.end_time.strftime('%H:%M')}"
        return "—"

    @display(description="Рабочий день", boolean=True)
    def is_working_badge(self, obj):
        return obj.is_working


@admin.register(Appointment)
class AppointmentAdmin(ModelAdmin):
    list_display = ["id", "client", "master", "service", "date", "start_time", "status_badge"]
    list_filter = ["status", ("date", RangeDateFilter), "service"]
    search_fields = ["client__email", "master__user__email"]
    date_hierarchy = "date"
    readonly_fields = ["created_at", "updated_at"]
    list_filter_submit = True
    list_per_page = 25

    fieldsets = (
        ("Основная информация", {
            "fields": ("client", "master", "service")
        }),
        ("Дата и время", {
            "fields": ("date", "start_time", "end_time")
        }),
        ("Статус", {
            "fields": ("status", "notes", "cancellation_reason")
        }),
        ("Системная информация", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @display(
        description="Статус",
        label={
            "pending": "warning",
            "confirmed": "info",
            "completed": "success",
            "cancelled": "danger",
            "no_show": "danger",
        }
    )
    def status_badge(self, obj):
        return obj.status


@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ["appointment", "rating_display", "comment_preview", "created_at"]
    list_filter = ["rating", ("created_at", RangeDateFilter)]
    search_fields = ["appointment__client__email", "comment"]
    list_filter_submit = True
    list_per_page = 25

    @display(description="Рейтинг")
    def rating_display(self, obj):
        stars = "★" * obj.rating + "☆" * (5 - obj.rating)
        return format_html('<span style="color: #f59e0b;">{}</span>', stars)

    @display(description="Комментарий")
    def comment_preview(self, obj):
        if obj.comment:
            return obj.comment[:50] + "..." if len(obj.comment) > 50 else obj.comment
        return "—"
