from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RangeDateFilter
from unfold.decorators import display

from .models import TodoItem


@admin.register(TodoItem)
class TodoItemAdmin(ModelAdmin):
    list_display = ["title", "master_name", "date", "time", "status_badge", "priority_badge", "created_at"]
    list_filter = ["status", "priority", ("date", RangeDateFilter)]
    search_fields = ["title", "description", "master__user__email"]
    readonly_fields = ["created_at", "updated_at"]
    list_filter_submit = True
    list_per_page = 25
    date_hierarchy = "date"

    fieldsets = (
        ("Основная информация", {
            "fields": ("master", "title", "description")
        }),
        ("Дата и время", {
            "fields": ("date", "time")
        }),
        ("Статус", {
            "fields": ("status", "priority")
        }),
        ("Служебная информация", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    @display(description="Мастер")
    def master_name(self, obj):
        return obj.master.user.full_name

    @display(description="Статус")
    def status_badge(self, obj):
        colors = {
            "todo": "bg-slate-100 text-slate-700",
            "in_progress": "bg-blue-100 text-blue-700",
            "done": "bg-green-100 text-green-700"
        }
        return obj.get_status_display()

    @display(description="Приоритет")
    def priority_badge(self, obj):
        return obj.get_priority_display()
