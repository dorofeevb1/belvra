"""
Models for beauty services.
"""

import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def _unique_upload_path(folder):
    def _path(instance, filename):
        ext = os.path.splitext(filename)[1]
        return f"{folder}/{uuid.uuid4().hex}{ext}"
    return _path

from apps.core.models import BaseModel
from apps.users.models import MasterProfile


class Category(BaseModel):
    """Service category model."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to=_unique_upload_path("categories"), null=True, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Service(BaseModel):
    """Beauty service model."""

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="services"
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to=_unique_upload_path("services"), null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.PositiveIntegerField(help_text="Duration in minutes")
    is_active = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Услуга"
        verbose_name_plural = "Услуги"
        ordering = ["category", "name"]

    def __str__(self):
        return self.name


class MasterService(BaseModel):
    """Link between masters and their offered services.

    Supports two modes:
    1. Catalog service: links to a Service from global catalog (service is set)
    2. Custom service: master creates their own service (service is null, custom_name is set)
    """

    master = models.ForeignKey(
        MasterProfile,
        on_delete=models.CASCADE,
        related_name="offered_services"
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        related_name="masters",
        null=True,
        blank=True,
        help_text="Link to catalog service (optional for custom services)"
    )
    # Custom service fields (used when service is null)
    custom_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Custom service name (for services not in catalog)"
    )
    custom_description = models.TextField(
        blank=True,
        help_text="Custom service description"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="custom_master_services",
        help_text="Category for custom services"
    )
    # Price and duration (override catalog service or set for custom)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Price (overrides catalog service price or sets for custom)"
    )
    duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Duration in minutes"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Услуга мастера"
        verbose_name_plural = "Услуги мастеров"
        constraints = [
            models.UniqueConstraint(
                fields=["master", "service"],
                condition=models.Q(service__isnull=False),
                name="unique_master_catalog_service"
            ),
            models.UniqueConstraint(
                fields=["master", "custom_name"],
                condition=models.Q(service__isnull=True, custom_name__gt=""),
                name="unique_master_custom_service"
            ),
        ]

    def __str__(self):
        name = self.name
        return f"{self.master.user.full_name} - {name}"

    def clean(self):
        if not self.service and not self.custom_name:
            raise ValidationError("Укажите услугу из каталога или своё название")

    @property
    def name(self):
        """Return service name (from catalog or custom)."""
        if self.service:
            return self.service.name
        return self.custom_name or "Без названия"

    @property
    def description(self):
        """Return service description (from catalog or custom)."""
        if self.service and not self.custom_description:
            return self.service.description
        return self.custom_description

    @property
    def actual_price(self):
        if self.price:
            return self.price
        if self.service and self.service.price:
            return self.service.price
        raise ValidationError("Цена не задана ни для мастера, ни в каталоге")

    @property
    def actual_duration(self):
        if self.duration:
            return self.duration
        if self.service and self.service.duration:
            return self.service.duration
        raise ValidationError("Длительность не задана ни для мастера, ни в каталоге")

    @property
    def is_custom(self):
        """Return True if this is a custom service (not from catalog)."""
        return self.service is None


class PortfolioItem(BaseModel):
    """Portfolio item for master's work showcase."""

    master = models.ForeignKey(
        MasterProfile,
        on_delete=models.CASCADE,
        related_name="portfolio_items"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to=_unique_upload_path("portfolio"))
    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="portfolio_items"
    )
    hashtags = models.JSONField(default=list, blank=True)
    likes_count = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)
    is_pinned = models.BooleanField(default=False, help_text="Закреплено наверху")

    class Meta:
        verbose_name = "Работа в портфолио"
        verbose_name_plural = "Работы в портфолио"
        ordering = ["-is_pinned", "-created_at"]

    def __str__(self):
        return f"{self.master.user.full_name} - {self.title}"


class PortfolioLike(models.Model):
    """Track individual likes to prevent duplicates."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="portfolio_likes",
    )
    portfolio_item = models.ForeignKey(
        PortfolioItem,
        on_delete=models.CASCADE,
        related_name="likes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Лайк портфолио"
        verbose_name_plural = "Лайки портфолио"
        unique_together = ("user", "portfolio_item")

    def __str__(self):
        return f"{self.user} -> {self.portfolio_item}"
