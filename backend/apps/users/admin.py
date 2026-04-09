from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RangeDateFilter
from unfold.decorators import display

from .models import (
    MasterLocation,
    MasterNotificationSettings,
    MasterProfile,
    MasterSocialLinks,
    User,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    list_display = ["email", "first_name", "last_name", "role_badge", "is_active_badge", "is_deleted_badge", "is_early_adopter", "created_at"]
    list_filter = ["role", "is_active", "is_staff", "is_verified", "is_early_adopter", "is_deleted", ("created_at", RangeDateFilter)]
    search_fields = ["email", "first_name", "last_name", "phone"]
    ordering = ["-created_at"]
    list_filter_submit = True
    list_per_page = 25
    readonly_fields = ["deleted_at"]

    def get_queryset(self, request):
        """Use all_objects to show soft-deleted users in admin."""
        return User.all_objects.all()

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Личная информация", {"fields": ("first_name", "last_name", "phone", "avatar")}),
        ("Права доступа", {"fields": ("role", "is_active", "is_staff", "is_superuser", "is_verified")}),
        ("Подписка", {"fields": ("is_early_adopter",)}),
        ("Soft delete", {"fields": ("is_deleted", "deleted_at")}),
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

    @display(description="Удалён", boolean=True)
    def is_deleted_badge(self, obj):
        return obj.is_deleted


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


@admin.register(MasterLocation)
class MasterLocationAdmin(ModelAdmin):
    list_display = ["master", "address"]
    search_fields = ["master__user__email", "address"]


@admin.register(MasterSocialLinks)
class MasterSocialLinksAdmin(ModelAdmin):
    list_display = ["master", "telegram", "instagram", "vk", "whatsapp"]
    search_fields = ["master__user__email"]


@admin.register(MasterNotificationSettings)
class MasterNotificationSettingsAdmin(ModelAdmin):
    list_display = ["master", "email_notifications", "sms_notifications", "push_notifications", "reminder_hours"]
    search_fields = ["master__user__email"]
