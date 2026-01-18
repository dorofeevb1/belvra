from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RangeDateFilter
from unfold.decorators import display

from .models import Category, MasterService, PortfolioItem, Service


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ["name", "slug", "is_active_badge", "order", "services_count"]
    list_filter = ["is_active"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["order", "name"]
    list_filter_submit = True

    @display(description="Активна", boolean=True)
    def is_active_badge(self, obj):
        return obj.is_active

    @display(description="Услуг")
    def services_count(self, obj):
        count = obj.services.count()
        return format_html('<span class="badge">{}</span>', count)


@admin.register(Service)
class ServiceAdmin(ModelAdmin):
    list_display = ["name", "category", "price_display", "duration_display", "is_active_badge", "is_popular_badge"]
    list_filter = ["category", "is_active", "is_popular"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["category", "name"]
    list_filter_submit = True
    list_per_page = 25

    @display(description="Цена")
    def price_display(self, obj):
        return f"{obj.price} ₽"

    @display(description="Длительность")
    def duration_display(self, obj):
        return f"{obj.duration} мин"

    @display(description="Активна", boolean=True)
    def is_active_badge(self, obj):
        return obj.is_active

    @display(description="Популярная", boolean=True)
    def is_popular_badge(self, obj):
        return obj.is_popular


@admin.register(MasterService)
class MasterServiceAdmin(ModelAdmin):
    list_display = ["master", "service", "price_display", "duration_display"]
    list_filter = ["service__category"]
    search_fields = ["master__user__email", "service__name"]
    autocomplete_fields = ["master", "service"]
    list_filter_submit = True

    @display(description="Цена")
    def price_display(self, obj):
        return f"{obj.price} ₽"

    @display(description="Длительность")
    def duration_display(self, obj):
        return f"{obj.duration} мин"


@admin.register(PortfolioItem)
class PortfolioItemAdmin(ModelAdmin):
    list_display = ["title", "master", "service", "likes_count", "is_published_badge", "created_at"]
    list_filter = ["is_published", "service", ("created_at", RangeDateFilter)]
    search_fields = ["title", "description", "master__user__email"]
    autocomplete_fields = ["master", "service"]
    list_filter_submit = True
    list_per_page = 25
    readonly_fields = ["likes_count", "created_at"]

    fieldsets = (
        ("Основная информация", {
            "fields": ("master", "title", "description", "image")
        }),
        ("Связи", {
            "fields": ("service", "hashtags")
        }),
        ("Статистика", {
            "fields": ("likes_count", "is_published", "created_at")
        }),
    )

    @display(description="Опубликовано", boolean=True)
    def is_published_badge(self, obj):
        return obj.is_published
