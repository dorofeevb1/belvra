from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RangeDateFilter
from unfold.decorators import display

from .models import MasterProfile, User


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    list_display = ["email", "first_name", "last_name", "role_badge", "is_active_badge", "created_at"]
    list_filter = ["role", "is_active", "is_staff", "is_verified", ("created_at", RangeDateFilter)]
    search_fields = ["email", "first_name", "last_name", "phone"]
    ordering = ["-created_at"]
    list_filter_submit = True
    list_per_page = 25

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Личная информация", {"fields": ("first_name", "last_name", "phone", "avatar")}),
        ("Права доступа", {"fields": ("role", "is_active", "is_staff", "is_superuser", "is_verified")}),
        ("Группы", {"fields": ("groups", "user_permissions")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "password1", "password2", "role"),
        }),
    )

    @display(description="Роль", label={"client": "info", "master": "success", "admin": "warning"})
    def role_badge(self, obj):
        return obj.role

    @display(description="Активен", boolean=True)
    def is_active_badge(self, obj):
        return obj.is_active


@admin.register(MasterProfile)
class MasterProfileAdmin(ModelAdmin):
    list_display = ["user", "specialization", "rating_display", "is_available_badge"]
    list_filter = ["is_available", "experience_years"]
    search_fields = ["user__email", "user__first_name", "specialization"]
    list_filter_submit = True

    @display(description="Рейтинг")
    def rating_display(self, obj):
        if obj.rating:
            stars = "★" * int(obj.rating) + "☆" * (5 - int(obj.rating))
            return format_html('<span style="color: #f59e0b;">{}</span> ({})', stars, obj.rating)
        return "—"

    @display(description="Доступен", boolean=True)
    def is_available_badge(self, obj):
        return obj.is_available
