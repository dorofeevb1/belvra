from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
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
    # Write-only fields for master profile updates
    specialization = serializers.CharField(write_only=True, required=False, allow_blank=True)
    bio = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "id", "email", "phone", "first_name", "last_name",
            "full_name", "avatar", "role", "is_verified", "created_at",
            "master_profile_id", "has_master_profile", "specialization", "bio",
            "address", "latitude", "longitude", "rating", "reviews_count",
            "subscription"
        ]
        read_only_fields = ["id", "email", "role", "is_verified", "created_at"]

    def get_master_profile_id(self, obj):
        """Return master profile ID if user is a master."""
        if obj.role == 'master' and hasattr(obj, 'master_profile'):
            return str(obj.master_profile.id)
        return None

    def get_has_master_profile(self, obj):
        """Return True if user has a master profile (can switch to master mode)."""
        return hasattr(obj, 'master_profile') and obj.master_profile is not None

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

        # Update user fields
        instance = super().update(instance, validated_data)

        # Update master profile if user is a master
        if instance.role == 'master' and hasattr(instance, 'master_profile'):
            master_profile = instance.master_profile
            if specialization is not None:
                master_profile.specialization = specialization
            if bio is not None:
                master_profile.bio = bio
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

    class Meta:
        model = User
        fields = [
            "email", "password", "password_confirm",
            "first_name", "last_name", "phone", "role"
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Пароли не совпадают"})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


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


class MasterProfileSerializer(serializers.ModelSerializer):
    """Serializer for MasterProfile."""

    user = UserSerializer(read_only=True)

    class Meta:
        model = MasterProfile
        fields = [
            "id", "user", "bio", "experience_years",
            "specialization", "rating", "reviews_count", "is_available",
            "address", "latitude", "longitude"
        ]
        read_only_fields = ["id", "rating", "reviews_count"]


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
    """Serializer for email verification."""

    token = serializers.CharField()


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
