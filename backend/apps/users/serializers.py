from decimal import Decimal

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import FavoriteMaster, MasterProfile, User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""

    full_name = serializers.ReadOnlyField()
    master_profile_id = serializers.SerializerMethodField()
    subscription = serializers.SerializerMethodField()
    has_master_profile = serializers.SerializerMethodField()
    # Master profile read fields
    address = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    social_links = serializers.SerializerMethodField()
    notification_settings = serializers.SerializerMethodField()
    # Master profile read fields (specialization, bio)
    specialization = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    # Write-only fields for master profile updates
    specialization_write = serializers.CharField(write_only=True, required=False, allow_blank=True, source='specialization')
    bio_write = serializers.CharField(write_only=True, required=False, allow_blank=True, source='bio')
    address_write = serializers.CharField(write_only=True, required=False, allow_blank=True, source='address')
    latitude_write = serializers.DecimalField(
        max_digits=9, decimal_places=6, write_only=True, required=False, allow_null=True
    )
    longitude_write = serializers.DecimalField(
        max_digits=9, decimal_places=6, write_only=True, required=False, allow_null=True
    )
    # Social links write fields
    telegram = serializers.CharField(write_only=True, required=False, allow_blank=True)
    instagram = serializers.CharField(write_only=True, required=False, allow_blank=True)
    vk = serializers.CharField(write_only=True, required=False, allow_blank=True)
    whatsapp = serializers.CharField(write_only=True, required=False, allow_blank=True)
    # Notification settings write fields
    email_notifications = serializers.BooleanField(write_only=True, required=False)
    sms_notifications = serializers.BooleanField(write_only=True, required=False)
    push_notifications = serializers.BooleanField(write_only=True, required=False)
    reminder_hours = serializers.IntegerField(write_only=True, required=False)
    # Master profile extra fields
    experience_years = serializers.SerializerMethodField()
    experience_years_write = serializers.IntegerField(write_only=True, required=False, min_value=0)
    is_available = serializers.BooleanField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "id", "email", "phone", "first_name", "last_name",
            "full_name", "avatar", "role", "is_verified",
            "referral_code", "is_early_adopter", "created_at",
            "master_profile_id", "has_master_profile", "specialization", "specialization_write",
            "bio", "bio_write",
            "address", "address_write", "latitude", "latitude_write",
            "longitude", "longitude_write", "rating", "reviews_count",
            "social_links", "notification_settings",
            "telegram", "instagram", "vk", "whatsapp",
            "email_notifications", "sms_notifications", "push_notifications", "reminder_hours",
            "experience_years", "experience_years_write", "is_available",
            "subscription"
        ]
        read_only_fields = ["id", "email", "role", "is_verified", "referral_code", "is_early_adopter", "created_at"]

    def get_master_profile_id(self, obj):
        """Return master profile ID if user is a master."""
        if obj.role == 'master' and hasattr(obj, 'master_profile'):
            return str(obj.master_profile.id)
        return None

    def get_has_master_profile(self, obj):
        """Return True if user has a master profile (can switch to master mode)."""
        return hasattr(obj, 'master_profile') and obj.master_profile is not None

    def get_experience_years(self, obj):
        if obj.role == 'master' and hasattr(obj, 'master_profile'):
            return obj.master_profile.experience_years or 0
        return 0

    def get_specialization(self, obj):
        if obj.role == 'master' and hasattr(obj, 'master_profile'):
            return obj.master_profile.specialization or ''
        return ''

    def get_bio(self, obj):
        if obj.role == 'master' and hasattr(obj, 'master_profile'):
            return obj.master_profile.bio or ''
        return ''

    def get_address(self, obj):
        if obj.role == 'master' and hasattr(obj, 'master_profile'):
            return obj.master_profile.address
        return None

    def get_latitude(self, obj):
        if obj.role == 'master' and hasattr(obj, 'master_profile'):
            return float(obj.master_profile.latitude) if obj.master_profile.latitude else None
        return None

    def get_longitude(self, obj):
        if obj.role == 'master' and hasattr(obj, 'master_profile'):
            return float(obj.master_profile.longitude) if obj.master_profile.longitude else None
        return None

    def get_rating(self, obj):
        if obj.role == 'master' and hasattr(obj, 'master_profile'):
            return float(obj.master_profile.rating)
        return None

    def get_reviews_count(self, obj):
        if obj.role == 'master' and hasattr(obj, 'master_profile'):
            return obj.master_profile.reviews_count
        return None

    def get_social_links(self, obj):
        if obj.role == 'master' and hasattr(obj, 'master_profile'):
            mp = obj.master_profile
            return {
                "telegram": mp.telegram or "",
                "instagram": mp.instagram or "",
                "vk": mp.vk or "",
                "whatsapp": mp.whatsapp or ""
            }
        return None

    def get_notification_settings(self, obj):
        if obj.role == 'master' and hasattr(obj, 'master_profile'):
            mp = obj.master_profile
            return {
                "emailNotifications": mp.email_notifications,
                "smsNotifications": mp.sms_notifications,
                "pushNotifications": mp.push_notifications,
                "reminderHours": mp.reminder_hours
            }
        return None

    def get_subscription(self, obj):
        """Return subscription info if user has one."""
        if hasattr(obj, 'subscription'):
            subscription = obj.subscription
            return {
                "id": str(subscription.id),
                "plan_name": subscription.plan.name,
                "plan_tier": subscription.plan.tier,
                "status": subscription.status,
                "is_active": subscription.is_active,
                "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            }
        return None

    def update(self, instance, validated_data):
        """Update user and optionally master profile."""
        # Extract master profile fields
        specialization = validated_data.pop('specialization', None)
        bio = validated_data.pop('bio', None)
        address = validated_data.pop('address', None)
        latitude = validated_data.pop('latitude_write', None)
        longitude = validated_data.pop('longitude_write', None)
        # Social links
        telegram = validated_data.pop('telegram', None)
        instagram = validated_data.pop('instagram', None)
        vk = validated_data.pop('vk', None)
        whatsapp = validated_data.pop('whatsapp', None)
        # Notification settings
        email_notifications = validated_data.pop('email_notifications', None)
        sms_notifications = validated_data.pop('sms_notifications', None)
        push_notifications = validated_data.pop('push_notifications', None)
        reminder_hours = validated_data.pop('reminder_hours', None)
        experience_years = validated_data.pop('experience_years_write', None)
        is_available = validated_data.pop('is_available', None)

        # Update user fields
        instance = super().update(instance, validated_data)

        # Update master profile if user is a master
        if instance.role == 'master' and hasattr(instance, 'master_profile'):
            master_profile = instance.master_profile
            if specialization is not None:
                master_profile.specialization = specialization
            if bio is not None:
                master_profile.bio = bio
            if address is not None:
                master_profile.address = address
                if not address:
                    master_profile.latitude = None
                    master_profile.longitude = None
            if latitude is not None:
                master_profile.latitude = Decimal(str(latitude))
            if longitude is not None:
                master_profile.longitude = Decimal(str(longitude))
            # Social links
            if telegram is not None:
                master_profile.telegram = telegram
            if instagram is not None:
                master_profile.instagram = instagram
            if vk is not None:
                master_profile.vk = vk
            if whatsapp is not None:
                master_profile.whatsapp = whatsapp
            # Notification settings
            if email_notifications is not None:
                master_profile.email_notifications = email_notifications
            if sms_notifications is not None:
                master_profile.sms_notifications = sms_notifications
            if push_notifications is not None:
                master_profile.push_notifications = push_notifications
            if reminder_hours is not None:
                master_profile.reminder_hours = reminder_hours
            if experience_years is not None:
                master_profile.experience_years = experience_years
            if is_available is not None:
                master_profile.is_available = is_available
            master_profile.save()

        return instance


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(
        choices=[("client", "Клиент"), ("master", "Мастер")],
        default="client"
    )
    accept_privacy = serializers.BooleanField(write_only=True)
    accept_terms = serializers.BooleanField(write_only=True)
    referral_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "email", "password", "password_confirm",
            "first_name", "last_name", "phone", "role",
            "accept_privacy", "accept_terms", "referral_code"
        ]

    def validate_accept_privacy(self, value):
        if not value:
            raise serializers.ValidationError(
                "Необходимо дать согласие на обработку персональных данных"
            )
        return value

    def validate_accept_terms(self, value):
        if not value:
            raise serializers.ValidationError(
                "Необходимо принять пользовательское соглашение"
            )
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Пароли не совпадают"})
        return attrs

    def validate_referral_code(self, value):
        if value:
            value = value.strip().upper()
            if not User.objects.filter(referral_code=value).exists():
                raise serializers.ValidationError("Реферальный код не найден")
        return value

    def create(self, validated_data):
        from django.db.models import Count

        validated_data.pop("accept_privacy", None)
        validated_data.pop("accept_terms", None)
        ref_code = validated_data.pop("referral_code", None)
        now = timezone.now()
        validated_data["privacy_accepted_at"] = now
        validated_data["terms_accepted_at"] = now
        validated_data["privacy_version_accepted"] = "1.1"
        validated_data["terms_version_accepted"] = "1.1"

        # Link referrer (prevent self-referral by checking email)
        if ref_code:
            referrer = User.objects.filter(referral_code=ref_code).first()
            if referrer and referrer.email != validated_data.get("email"):
                validated_data["referred_by"] = referrer

        # Check early adopter (first 50 users) with atomic count
        # Materialize the queryset with list() to ensure row-level locks
        # are actually acquired before checking the count, preventing
        # race conditions where concurrent registrations both see < 50.
        with transaction.atomic():
            early_adopters = list(
                User.objects.select_for_update()
                .filter(is_early_adopter=True)
                .values_list("id", flat=True)
            )
            if len(early_adopters) < 50:
                validated_data["is_early_adopter"] = True

            user = User.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(email=attrs["email"], password=attrs["password"])
        if not user:
            raise serializers.ValidationError("Неверный email или пароль")
        if not user.is_active:
            raise serializers.ValidationError("Аккаунт деактивирован")
        attrs["user"] = user
        return attrs


class TokenSerializer(serializers.Serializer):
    """Serializer for token response."""

    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()

    @classmethod
    def get_token(cls, user):
        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data
        }


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Неверный текущий пароль")
        return value


class PublicUserSerializer(serializers.ModelSerializer):
    """User data visible to everyone (no PII)."""
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = ["id", "full_name", "avatar", "role"]
        read_only_fields = fields


class MasterProfileSerializer(serializers.ModelSerializer):
    """Serializer for MasterProfile."""

    user = UserSerializer(read_only=True)
    is_pro = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = MasterProfile
        fields = [
            "id", "user", "bio", "experience_years",
            "specialization", "rating", "reviews_count", "is_available",
            "address", "latitude", "longitude", "is_pro", "distance_km"
        ]
        read_only_fields = ["id", "rating", "reviews_count"]

    def get_is_pro(self, obj):
        sub = getattr(obj.user, "subscription", None)
        return bool(sub and sub.is_active and sub.plan.pro_badge)

    def get_distance_km(self, obj):
        dist = getattr(obj, "distance_km", None)
        return round(dist, 1) if dist is not None else None


class PublicMasterProfileSerializer(serializers.ModelSerializer):
    """Master profile for public listings (no email/phone)."""
    user = PublicUserSerializer(read_only=True)
    is_pro = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = MasterProfile
        fields = [
            "id", "user", "bio", "experience_years",
            "specialization", "rating", "reviews_count", "is_available",
            "address", "latitude", "longitude", "is_pro", "distance_km"
        ]
        read_only_fields = ["id", "rating", "reviews_count"]

    def get_is_pro(self, obj):
        sub = getattr(obj.user, "subscription", None)
        return bool(sub and sub.is_active and sub.plan.pro_badge)

    def get_distance_km(self, obj):
        dist = getattr(obj, "distance_km", None)
        return round(dist, 1) if dist is not None else None


class PublicMasterWithDistanceSerializer(serializers.ModelSerializer):
    """Master profile with distance for public geo-search (no email/phone)."""
    user = PublicUserSerializer(read_only=True)
    distance_km = serializers.FloatField(read_only=True)

    class Meta:
        model = MasterProfile
        fields = [
            "id", "user", "bio", "experience_years",
            "specialization", "rating", "reviews_count", "is_available",
            "address", "latitude", "longitude", "distance_km"
        ]
        read_only_fields = ["id", "rating", "reviews_count", "distance_km"]


class MasterWithDistanceSerializer(serializers.ModelSerializer):
    """Serializer for MasterProfile with distance field for geo-search."""

    user = UserSerializer(read_only=True)
    distance_km = serializers.FloatField(read_only=True)

    class Meta:
        model = MasterProfile
        fields = [
            "id", "user", "bio", "experience_years",
            "specialization", "rating", "reviews_count", "is_available",
            "address", "latitude", "longitude", "distance_km"
        ]
        read_only_fields = ["id", "rating", "reviews_count", "distance_km"]


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request."""

    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation."""

    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, validators=[validate_password])


class EmailVerificationSerializer(serializers.Serializer):
    """Serializer for email verification with 6-digit code."""

    email = serializers.EmailField()
    code = serializers.CharField(max_length=6, min_length=6)


class FavoriteMasterSerializer(serializers.ModelSerializer):
    """Serializer for FavoriteMaster."""

    master = MasterProfileSerializer(read_only=True)
    master_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = FavoriteMaster
        fields = ["id", "master", "master_id", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_master_id(self, value):
        try:
            MasterProfile.objects.get(id=value)
        except MasterProfile.DoesNotExist:
            raise serializers.ValidationError("Мастер не найден")
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        master_id = validated_data.pop("master_id")
        master = MasterProfile.objects.get(id=master_id)

        # Check if already favorited
        if FavoriteMaster.objects.filter(user=user, master=master).exists():
            raise serializers.ValidationError({"detail": "Мастер уже в избранном"})

        return FavoriteMaster.objects.create(user=user, master=master)
