"""
Custom User model and related models.
"""

import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

from apps.core.models import TimeStampedModel


class UserManager(BaseUserManager):
    """Custom user manager."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", User.Role.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """Custom User model with email authentication."""

    class Role(models.TextChoices):
        CLIENT = "client", "Клиент"
        MASTER = "master", "Мастер"
        ADMIN = "admin", "Администратор"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    phone = models.CharField(max_length=20, blank=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CLIENT)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["-created_at"]

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_master(self):
        return self.role == self.Role.MASTER

    @property
    def is_client(self):
        return self.role == self.Role.CLIENT


class MasterProfile(TimeStampedModel):
    """Extended profile for masters."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="master_profile"
    )
    bio = models.TextField(blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    specialization = models.CharField(max_length=255, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    reviews_count = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)
    address = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Social links
    telegram = models.CharField(max_length=100, blank=True)
    instagram = models.CharField(max_length=100, blank=True)
    vk = models.CharField(max_length=200, blank=True)
    whatsapp = models.CharField(max_length=20, blank=True)

    # Notification settings
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    push_notifications = models.BooleanField(default=True)
    reminder_hours = models.PositiveIntegerField(default=24)

    # Payment settings
    online_payments_enabled = models.BooleanField(default=False)
    prepayment_required = models.BooleanField(default=False)
    prepayment_percent = models.PositiveIntegerField(default=30)
    accept_card = models.BooleanField(default=True)
    accept_sbp = models.BooleanField(default=True)
    accept_yoomoney = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Профиль мастера"
        verbose_name_plural = "Профили мастеров"

    def __str__(self):
        return f"Профиль мастера: {self.user.full_name}"


class FavoriteMaster(TimeStampedModel):
    """Model to track user's favorite masters."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="favorite_masters"
    )
    master = models.ForeignKey(
        MasterProfile,
        on_delete=models.CASCADE,
        related_name="favorited_by"
    )

    class Meta:
        verbose_name = "Избранный мастер"
        verbose_name_plural = "Избранные мастера"
        unique_together = ["user", "master"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} -> {self.master.user.full_name}"
