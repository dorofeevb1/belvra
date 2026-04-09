import logging
import math
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import logout
from django.core.cache import cache
from django.db import transaction
from django.db.models import Case, F, FloatField, IntegerField, Q, Value, When
from django.db.models.functions import ACos, Cos, Radians, Sin
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.tasks import (
    send_email_verification_code_task,
    send_password_reset_email_task,
    send_welcome_email_task,
)

from .models import BlockedUser, FavoriteMaster, MasterProfile, User
from .serializers import (
    ChangePasswordSerializer,
    EmailVerificationSerializer,
    FavoriteMasterSerializer,
    LoginSerializer,
    MasterProfileSerializer,
    MasterWithDistanceSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PublicMasterProfileSerializer,
    PublicMasterWithDistanceSerializer,
    TokenSerializer,
    UserCreateSerializer,
    UserSerializer,
)

logger = logging.getLogger(__name__)


class LoginThrottle(AnonRateThrottle):
    rate = '10/min'


class RegisterThrottle(AnonRateThrottle):
    rate = '5/min'


@extend_schema(
    tags=["Аутентификация"],
    summary="Регистрация пользователя",
    description="Создание нового аккаунта пользователя",
    responses={201: TokenSerializer}
)
class RegisterView(generics.CreateAPIView):
    """User registration endpoint."""

    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [AllowAny]
    throttle_classes = [RegisterThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Grant Pro subscription
        if user.is_early_adopter:
            # First 50 users — lifetime Pro
            self._grant_early_adopter_pro(user)
        else:
            # All other new users — 1 month free Pro trial
            self._grant_free_trial_pro(user)

        # Create referral record
        if user.referred_by:
            from apps.subscriptions.models import Referral
            Referral.objects.get_or_create(
                referrer=user.referred_by,
                referred_user=user,
                defaults={"reward_type": Referral.RewardType.FREE_MONTH_PRO}
            )

        # Generate 6-digit verification code
        code = f"{secrets.randbelow(900000) + 100000}"
        cache_key = f"email_verify_code_{user.id}"
        cache.set(cache_key, code, timeout=600)  # 10 minutes

        # Send verification code via email
        send_email_verification_code_task.delay(str(user.id), code)

        token_data = TokenSerializer.get_token(user)
        return Response({
            **token_data,
            "verification_email": user.email,
            "is_early_adopter": user.is_early_adopter,
            "referral_code": user.referral_code,
        }, status=status.HTTP_201_CREATED)

    @staticmethod
    def _grant_early_adopter_pro(user):
        """Grant lifetime Pro subscription to early adopter."""
        from apps.subscriptions.models import Subscription, SubscriptionPlan
        from decimal import Decimal

        user_type = SubscriptionPlan.UserType.MASTER if user.role == "master" else SubscriptionPlan.UserType.CLIENT

        pro_plan, _ = SubscriptionPlan.objects.get_or_create(
            tier=SubscriptionPlan.Tier.PRO,
            user_type=user_type,
            period=SubscriptionPlan.Period.MONTHLY,
            defaults={
                "name": f"Pro ({user_type})",
                "price": Decimal("0"),
                "max_appointments_per_month": 0,
                "max_services_count": 0,
                "max_portfolio_items": 0,
                "commission_percent": Decimal("3.00"),
                "search_boost_enabled": True,
                "analytics_level": SubscriptionPlan.AnalyticsLevel.ADVANCED,
                "ai_assistant_enabled": True,
                "advanced_notifications": True,
                "export_data_enabled": True,
                "priority_booking": True,
                "cashback_percent": Decimal("5.00"),
                "extended_search": True,
                "history_months": 0,
                "client_stats_enabled": True,
                "max_favorites": 0,
                "pro_badge": True,
                "client_notes_enabled": True,
                "max_pinned_portfolio": 3,
                "rebooking_reminder_enabled": True,
            }
        )

        Subscription.objects.get_or_create(
            user=user,
            defaults={
                "plan": pro_plan,
                "status": Subscription.Status.ACTIVE,
                "current_period_start": timezone.now(),
                "current_period_end": None,  # Lifetime — never expires
                "auto_renew": False,
            }
        )

    @staticmethod
    def _grant_free_trial_pro(user):
        """Grant 1-month free Pro trial to new user."""
        from apps.subscriptions.models import Subscription, SubscriptionPlan
        from decimal import Decimal

        user_type = SubscriptionPlan.UserType.MASTER if user.role == "master" else SubscriptionPlan.UserType.CLIENT

        pro_plan, _ = SubscriptionPlan.objects.get_or_create(
            tier=SubscriptionPlan.Tier.PRO,
            user_type=user_type,
            period=SubscriptionPlan.Period.MONTHLY,
            defaults={
                "name": f"Pro ({user_type})",
                "price": Decimal("0"),
                "max_appointments_per_month": 0,
                "max_services_count": 0,
                "max_portfolio_items": 0,
                "commission_percent": Decimal("3.00"),
                "search_boost_enabled": True,
                "analytics_level": SubscriptionPlan.AnalyticsLevel.ADVANCED,
                "ai_assistant_enabled": True,
                "advanced_notifications": True,
                "export_data_enabled": True,
                "priority_booking": True,
                "cashback_percent": Decimal("5.00"),
                "extended_search": True,
                "history_months": 0,
                "client_stats_enabled": True,
                "max_favorites": 0,
                "pro_badge": True,
                "client_notes_enabled": True,
                "max_pinned_portfolio": 3,
                "rebooking_reminder_enabled": True,
            }
        )

        now = timezone.now()
        Subscription.objects.get_or_create(
            user=user,
            defaults={
                "plan": pro_plan,
                "status": Subscription.Status.ACTIVE,
                "current_period_start": now,
                "current_period_end": now + timedelta(days=30),
                "auto_renew": False,
            }
        )


@extend_schema(
    tags=["Аутентификация"],
    summary="Вход в систему",
    description="Аутентификация пользователя по email и паролю",
    request=LoginSerializer,
    responses={200: TokenSerializer}
)
class LoginView(APIView):
    """User login endpoint."""

    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token_data = TokenSerializer.get_token(user)
        return Response(token_data)


@extend_schema(
    tags=["Аутентификация"],
    summary="Выход из системы",
    description="Выход пользователя и инвалидация refresh токена"
)
class LogoutView(APIView):
    """User logout endpoint."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            logger.exception("Failed to blacklist refresh token during logout")
        logout(request)
        return Response({"detail": "Вы успешно вышли"}, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(
        tags=["Профиль"],
        summary="Получить профиль",
        description="Получение данных текущего пользователя"
    ),
    put=extend_schema(
        tags=["Профиль"],
        summary="Обновить профиль",
        description="Полное обновление профиля пользователя"
    ),
    patch=extend_schema(
        tags=["Профиль"],
        summary="Частичное обновление профиля",
        description="Частичное обновление данных профиля"
    )
)
class UserProfileView(generics.RetrieveUpdateAPIView):
    """Current user profile endpoint."""

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


@extend_schema(
    tags=["Профиль"],
    summary="Загрузить аватар",
    description="Загрузка нового аватара пользователя"
)
class UploadAvatarView(APIView):
    """Upload user avatar endpoint."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if 'avatar' not in request.FILES:
            return Response(
                {"detail": "Файл аватара не предоставлен"},
                status=status.HTTP_400_BAD_REQUEST
            )

        avatar_file = request.FILES['avatar']

        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if avatar_file.content_type not in allowed_types:
            return Response(
                {"detail": "Недопустимый формат файла. Разрешены: JPEG, PNG, GIF, WebP"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate file size (max 5MB)
        if avatar_file.size > 5 * 1024 * 1024:
            return Response(
                {"detail": "Файл слишком большой. Максимум 5MB"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Delete old avatar if exists
        user = request.user
        if user.avatar:
            user.avatar.delete(save=False)

        # Save new avatar
        user.avatar = avatar_file
        user.save()

        return Response({
            "detail": "Аватар успешно загружен",
            "avatar": request.build_absolute_uri(user.avatar.url) if user.avatar else None
        })

    def delete(self, request):
        """Delete user avatar."""
        user = request.user
        if user.avatar:
            user.avatar.delete(save=True)
        return Response({"detail": "Аватар удалён"})


@extend_schema(
    tags=["Профиль"],
    summary="Изменить пароль",
    description="Изменение пароля текущего пользователя"
)
class ChangePasswordView(APIView):
    """Change password endpoint."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response({"detail": "Пароль успешно изменён"})


@extend_schema(
    tags=["Мастера"],
    summary="Список мастеров",
    description="Поиск мастеров по тексту, геолокации и фильтрам",
    parameters=[
        OpenApiParameter(name="q", description="Текстовый поиск (имя, специализация, услуги)", required=False, type=str),
        OpenApiParameter(name="lat", description="Широта для поиска рядом", required=False, type=float),
        OpenApiParameter(name="lng", description="Долгота для поиска рядом", required=False, type=float),
        OpenApiParameter(name="radius_km", description="Радиус поиска в км (по умолчанию 10)", required=False, type=float),
        OpenApiParameter(name="min_rating", description="Мин. рейтинг (PRO)", required=False, type=float),
        OpenApiParameter(name="min_experience", description="Мин. опыт в годах (PRO)", required=False, type=float),
        OpenApiParameter(name="sort_by", description="Сортировка: rating, experience, reviews, distance (PRO)", required=False, type=str),
    ],
)
class MasterListView(generics.ListAPIView):
    """List all available masters with text search and geo-search."""

    serializer_class = PublicMasterProfileSerializer
    permission_classes = [AllowAny]

    EARTH_RADIUS_KM = 6371.0

    def get_queryset(self):
        queryset = MasterProfile.objects.filter(
            is_available=True,
            user__is_active=True
        ).select_related(
            "user", "user__subscription", "user__subscription__plan"
        ).annotate(
            boost=Case(
                When(
                    user__subscription__plan__search_boost_enabled=True,
                    user__subscription__status="active",
                    then=0,
                ),
                default=1,
                output_field=IntegerField(),
            )
        )

        # Text search (available to everyone)
        q = self.request.query_params.get("q", "").strip()
        if q:
            from apps.services.models import MasterService
            # Search in name, specialization, bio, and service names
            master_ids_from_services = MasterService.objects.filter(
                Q(custom_name__icontains=q) |
                Q(service__name__icontains=q)
            ).values_list("master_id", flat=True)

            queryset = queryset.filter(
                Q(user__first_name__icontains=q) |
                Q(user__last_name__icontains=q) |
                Q(specialization__icontains=q) |
                Q(bio__icontains=q) |
                Q(address__icontains=q) |
                Q(id__in=master_ids_from_services)
            )

        # Geo search (available to everyone)
        lat = self.request.query_params.get("lat")
        lng = self.request.query_params.get("lng")
        if lat and lng:
            try:
                lat_f = float(lat)
                lng_f = float(lng)
                radius_km = float(self.request.query_params.get("radius_km", 10))
                lat_rad = math.radians(lat_f)
                lng_rad = math.radians(lng_f)

                queryset = queryset.filter(
                    latitude__isnull=False,
                    longitude__isnull=False,
                ).annotate(
                    distance_km=Value(self.EARTH_RADIUS_KM) * ACos(
                        Sin(Value(lat_rad)) * Sin(Radians(F("latitude"))) +
                        Cos(Value(lat_rad)) * Cos(Radians(F("latitude"))) *
                        Cos(Radians(F("longitude")) - Value(lng_rad)),
                        output_field=FloatField()
                    )
                ).filter(distance_km__lte=radius_km).order_by("boost", "distance_km")
            except (ValueError, TypeError):
                queryset = queryset.order_by("boost", "-rating")
        else:
            queryset = queryset.order_by("boost", "-rating")

        return self._apply_extended_filters(queryset)

    def _apply_extended_filters(self, queryset):
        """Apply extended search filters for PRO clients."""
        user = self.request.user if self.request.user.is_authenticated else None
        has_extended = False
        if user:
            sub = getattr(user, "subscription", None)
            if sub and sub.is_active:
                has_extended = sub.plan.extended_search

        if not has_extended:
            return queryset

        min_rating = self.request.query_params.get("min_rating")
        min_experience = self.request.query_params.get("min_experience")
        sort_by = self.request.query_params.get("sort_by")

        if min_rating:
            try:
                queryset = queryset.filter(rating__gte=float(min_rating))
            except (ValueError, TypeError):
                pass
        if min_experience:
            try:
                queryset = queryset.filter(experience_years__gte=int(min_experience))
            except (ValueError, TypeError):
                pass
        if sort_by == "rating":
            queryset = queryset.order_by("boost", "-rating")
        elif sort_by == "experience":
            queryset = queryset.order_by("boost", "-experience_years")
        elif sort_by == "reviews":
            queryset = queryset.order_by("boost", "-reviews_count")

        return queryset


@extend_schema(
    tags=["Мастера"],
    summary="Информация о мастере",
    description="Получение детальной информации о мастере"
)
class MasterDetailView(generics.RetrieveAPIView):
    """Retrieve master details."""

    queryset = MasterProfile.objects.select_related("user", "user__subscription", "user__subscription__plan")
    serializer_class = PublicMasterProfileSerializer
    permission_classes = [AllowAny]


@extend_schema(
    tags=["Мастера"],
    summary="Поиск мастеров поблизости",
    description="Поиск мастеров в заданном радиусе от указанной точки (формула Haversine)",
    parameters=[
        OpenApiParameter(name="lat", description="Широта пользователя", required=True, type=float),
        OpenApiParameter(name="lng", description="Долгота пользователя", required=True, type=float),
        OpenApiParameter(name="radius_km", description="Радиус поиска в километрах (по умолчанию 10)", required=False, type=float),
    ]
)
class MasterGeoSearchView(generics.ListAPIView):
    """Search for masters within a given radius using Haversine formula."""

    serializer_class = PublicMasterWithDistanceSerializer
    permission_classes = [AllowAny]

    # Earth radius in kilometers
    EARTH_RADIUS_KM = 6371.0

    def get_queryset(self):
        try:
            lat = float(self.request.query_params.get("lat", 0))
            lng = float(self.request.query_params.get("lng", 0))
            radius_km = float(self.request.query_params.get("radius_km", 10))
        except (ValueError, TypeError):
            return MasterProfile.objects.none()

        if not lat or not lng:
            return MasterProfile.objects.none()

        # Filter masters with coordinates
        queryset = MasterProfile.objects.filter(
            is_available=True,
            user__is_active=True,
            latitude__isnull=False,
            longitude__isnull=False
        ).select_related("user")

        # Haversine formula using Django ORM
        # distance = R * acos(sin(lat1) * sin(lat2) + cos(lat1) * cos(lat2) * cos(lng2 - lng1))
        lat_rad = math.radians(lat)
        lng_rad = math.radians(lng)

        queryset = queryset.select_related(
            "user__subscription", "user__subscription__plan"
        ).annotate(
            distance_km=Value(self.EARTH_RADIUS_KM) * ACos(
                Sin(Value(lat_rad)) * Sin(Radians(F("latitude"))) +
                Cos(Value(lat_rad)) * Cos(Radians(F("latitude"))) *
                Cos(Radians(F("longitude")) - Value(lng_rad)),
                output_field=FloatField()
            ),
            boost=Case(
                When(
                    user__subscription__plan__search_boost_enabled=True,
                    user__subscription__status="active",
                    then=0,
                ),
                default=1,
                output_field=IntegerField(),
            )
        ).filter(
            distance_km__lte=radius_km
        ).order_by("boost", "distance_km")

        return queryset


class PasswordResetThrottle(AnonRateThrottle):
    rate = '3/min'


@extend_schema(
    tags=["Аутентификация"],
    summary="Запрос сброса пароля",
    description="Отправка email со ссылкой для сброса пароля"
)
class PasswordResetRequestView(APIView):
    """Request password reset - sends email with reset link."""

    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email, is_active=True)

            # Generate reset token
            token = secrets.token_urlsafe(32)

            # Store token in cache with 1 hour expiration
            cache_key = f"password_reset_{token}"
            cache.set(cache_key, user.id, timeout=3600)  # 1 hour

            # Build full reset URL
            reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

            # Send password reset email asynchronously
            send_password_reset_email_task.delay(str(user.id), reset_url)

            return Response({
                "detail": "Инструкции по сбросу пароля отправлены на email"
            })

        except User.DoesNotExist:
            # Don't reveal if user exists
            logger.debug("Password reset requested for non-existent email: %s", email)

        return Response({
            "detail": "Если пользователь с таким email существует, инструкции будут отправлены"
        })


@extend_schema(
    tags=["Аутентификация"],
    summary="Подтверждение сброса пароля",
    description="Установка нового пароля с использованием токена"
)
class PasswordResetConfirmView(APIView):
    """Confirm password reset with token and new password."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        # Verify token
        cache_key = f"password_reset_{token}"
        user_id = cache.get(cache_key)

        if not user_id:
            return Response(
                {"detail": "Недействительный или истёкший токен сброса"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(id=user_id, is_active=True)
            user.set_password(new_password)
            user.save()

            # Invalidate token
            cache.delete(cache_key)

            return Response({"detail": "Пароль успешно изменён"})

        except User.DoesNotExist:
            return Response(
                {"detail": "Пользователь не найден"},
                status=status.HTTP_400_BAD_REQUEST
            )


@extend_schema(
    tags=["Аутентификация"],
    summary="Проверка токена сброса",
    description="Проверка действительности токена сброса пароля"
)
class PasswordResetValidateTokenView(APIView):
    """Validate password reset token."""

    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token")

        if not token:
            return Response(
                {"valid": False, "detail": "Токен не указан"},
                status=status.HTTP_400_BAD_REQUEST
            )

        cache_key = f"password_reset_{token}"
        user_id = cache.get(cache_key)

        if user_id:
            return Response({"valid": True})

        return Response(
            {"valid": False, "detail": "Недействительный или истёкший токен"},
            status=status.HTTP_400_BAD_REQUEST
        )


class EmailVerifyThrottle(AnonRateThrottle):
    rate = '5/min'


@extend_schema(
    tags=["Аутентификация"],
    summary="Подтверждение email",
    description="Подтверждение email адреса с использованием токена"
)
class VerifyEmailView(APIView):
    """Verify email address with 6-digit code."""

    permission_classes = [AllowAny]
    throttle_classes = [EmailVerifyThrottle]

    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data["code"]
        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"detail": "Пользователь не найден"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if user.is_verified:
            return Response({"detail": "Email уже подтверждён"})

        cache_key = f"email_verify_code_{user.id}"
        stored_code = cache.get(cache_key)

        if not stored_code or stored_code != code:
            return Response(
                {"detail": "Неверный или истёкший код"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.is_verified = True
        user.save()
        cache.delete(cache_key)

        # Send welcome email after successful verification
        send_welcome_email_task.delay(str(user.id))

        return Response({"detail": "Email успешно подтверждён"})


@extend_schema(
    tags=["Аутентификация"],
    summary="Повторная отправка верификации",
    description="Повторная отправка письма для подтверждения email"
)
class ResendVerificationEmailView(APIView):
    """Resend verification email with new code."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        if user.is_verified:
            return Response(
                {"detail": "Email уже подтверждён"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate new 6-digit verification code
        code = f"{secrets.randbelow(900000) + 100000}"
        cache_key = f"email_verify_code_{user.id}"
        cache.set(cache_key, code, timeout=600)  # 10 minutes

        # Send verification code via email
        send_email_verification_code_task.delay(str(user.id), code)

        return Response({"detail": "Код подтверждения отправлен"})


@extend_schema(
    tags=["Профиль"],
    summary="Переключить роль",
    description="Переключить активную роль пользователя между клиентом и мастером"
)
class SwitchRoleView(APIView):
    """Switch user's active role between client and master."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        target_role = request.data.get("role")

        if target_role not in ("client", "master"):
            return Response(
                {"detail": "Укажите роль: 'client' или 'master'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if target_role == "master":
            if not hasattr(user, 'master_profile'):
                return Response(
                    {"detail": "У вас нет профиля мастера. Сначала станьте мастером."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        user.role = target_role
        user.save(update_fields=["role"])

        token_data = TokenSerializer.get_token(user)
        return Response(token_data)


@extend_schema(
    tags=["Профиль"],
    summary="Стать мастером",
    description="Создать профиль мастера для текущего пользователя (клиент становится также мастером)"
)
class BecomeMasterView(APIView):
    """Create a master profile for current user and switch to master role."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        if hasattr(user, 'master_profile'):
            # Already has master profile, just switch role
            user.role = 'master'
            user.save(update_fields=["role"])
            token_data = TokenSerializer.get_token(user)
            return Response(token_data)

        with transaction.atomic():
            MasterProfile.objects.create(user=user)
            user.role = 'master'
            user.save(update_fields=["role"])

        token_data = TokenSerializer.get_token(user)
        return Response(token_data, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=["Профиль"],
    summary="Удаление аккаунта",
    description="Полное удаление аккаунта и всех персональных данных пользователя (ФЗ-152)"
)
class DeleteAccountView(APIView):
    """Delete user account and all associated personal data."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        password = request.data.get("password")
        if not password:
            return Response(
                {"detail": "Для удаления аккаунта необходимо ввести пароль"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user
        if not user.check_password(password):
            return Response(
                {"detail": "Неверный пароль"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Blacklist all refresh tokens
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass

        # Delete user — CASCADE will remove all related data
        user.delete()

        return Response(
            {"detail": "Аккаунт и все персональные данные удалены"},
            status=status.HTTP_200_OK
        )


@extend_schema(
    tags=["Юридические документы"],
    summary="Юридические документы",
    description="Получение текстов политики конфиденциальности и пользовательского соглашения"
)
class LegalDocumentsView(APIView):
    """Return legal documents (privacy policy, terms of service)."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    PRIVACY_POLICY = {
        "title": "Политика конфиденциальности",
        "version": "2.0",
        "effective_date": "2026-04-06",
        "content": """
1. ОБЩИЕ ПОЛОЖЕНИЯ

1.1. Настоящая Политика конфиденциальности (далее — Политика) определяет порядок обработки и защиты персональных данных пользователей сервиса Belvra (далее — Сервис).

1.2. Оператором персональных данных является администрация Сервиса (далее — Оператор).

1.3. Политика разработана в соответствии с Федеральным законом от 27.07.2006 № 152-ФЗ «О персональных данных» и Федеральным законом от 27.07.2006 № 149-ФЗ «Об информации, информационных технологиях и о защите информации».

1.4. Контактные данные Оператора:
— Telegram: https://t.me/Dorof_hanzo
— Email: support@belvra.ru

2. ПЕРСОНАЛЬНЫЕ ДАННЫЕ, КОТОРЫЕ МЫ СОБИРАЕМ

2.1. При регистрации и использовании Сервиса мы собираем следующие персональные данные:
— Фамилия, имя;
— Адрес электронной почты (email);
— Номер телефона (при указании);
— Фотография профиля (при загрузке);
— Адрес оказания услуг (для мастеров);
— Геолокация (при использовании поиска мастеров поблизости);
— Данные о записях на услуги;
— Переписка в чате Сервиса (текстовые сообщения, фотографии, аудиосообщения, файлы);
— Токены устройств для отправки push-уведомлений.

2.2. В рамках реферальной программы мы собираем:
— Уникальный реферальный код пользователя;
— Информацию о том, кто пригласил пользователя;
— Статус и дату применения реферального вознаграждения.

2.3. При использовании ИИ-функций Сервиса данные обрабатываются с привлечением сторонних ИИ-провайдеров (Perplexity AI для текстовых запросов). Передаются исключительно те данные, которые Пользователь явно отправил для анализа. Изображения обрабатываются локально на серверах Сервиса и не передаются третьим лицам. Данные, переданные для ИИ-анализа, не хранятся после завершения обработки.

2.4. В рамках портфолио мастера мы собираем:
— Фотографии работ;
— Описания и хештеги к работам;
— Данные о лайках и просмотрах.

2.5. Мы не собираем и не храним полные данные банковских карт. Для обработки платежей за подписки используется сертифицированный платёжный провайдер АО «Т-Банк» (лицензия ЦБ РФ). Данные банковских карт вводятся на защищённой странице провайдера и не проходят через серверы Сервиса. Сервис не обрабатывает платежи между клиентами и мастерами — оплата услуг осуществляется напрямую.

2.6. Автоматически собираемые данные:
— IP-адрес;
— Тип и версия браузера;
— Тип устройства и операционная система;
— Дата и время обращения к Сервису;
— Данные файлов cookie (см. раздел 9).

3. ЦЕЛИ ОБРАБОТКИ ПЕРСОНАЛЬНЫХ ДАННЫХ

3.1. Персональные данные обрабатываются для следующих целей:
— Регистрация и аутентификация пользователя;
— Предоставление основного функционала Сервиса (запись на услуги, управление расписанием, чат);
— Связь между клиентами и мастерами;
— Отправка уведомлений о записях, подтверждениях и напоминаниях (email, push);
— Обработка платежей за подписки;
— Функционирование реферальной программы;
— ИИ-анализ фотографий и генерация рекомендаций (по запросу пользователя);
— Обеспечение безопасности Сервиса;
— Сбор анонимной статистики для улучшения качества Сервиса.

3.2. Автоматизированное принятие решений:
AI-функции Сервиса (поиск мастеров, анализ фото, генерация текстов) выполняют автоматизированную обработку данных. Результаты носят рекомендательный характер и не влекут юридических последствий для Пользователя. Пользователь вправе не использовать AI-функции.

4. ПРАВОВЫЕ ОСНОВАНИЯ ОБРАБОТКИ

4.1. Обработка персональных данных осуществляется на основании:
— Согласия субъекта персональных данных (п. 1 ч. 1 ст. 6 ФЗ-152);
— Исполнения договора, стороной которого является субъект персональных данных (п. 5 ч. 1 ст. 6 ФЗ-152);
— Законных интересов Оператора по обеспечению безопасности Сервиса (п. 7 ч. 1 ст. 6 ФЗ-152).

5. ХРАНЕНИЕ ПЕРСОНАЛЬНЫХ ДАННЫХ

5.1. Персональные данные хранятся на серверах, расположенных на территории Российской Федерации, в соответствии с ч. 5 ст. 18 ФЗ-152.

5.2. Сроки хранения персональных данных:
— Данные аккаунта: до удаления аккаунта пользователем;
— Сообщения чата: до удаления аккаунта;
— Данные о платежах за подписки: 3 года после совершения операции (требование законодательства);
— Логи сервера (IP-адреса, обращения): 90 дней;
— Данные аналитики (Яндекс.Метрика): определяются ООО «ЯНДЕКС».

5.3. При удалении аккаунта все персональные данные удаляются каскадно, за исключением данных о платежах, хранение которых требуется законодательством.

6. ЗАЩИТА ПЕРСОНАЛЬНЫХ ДАННЫХ

6.1. Оператор принимает необходимые организационные и технические меры для защиты персональных данных:
— Хеширование паролей (bcrypt);
— Использование протокола HTTPS с TLS 1.2+;
— Аутентификация с использованием JWT-токенов с ротацией;
— Разграничение прав доступа (роли: клиент, мастер, администратор);
— Защита от DDoS-атак (Cloudflare);
— Межсетевой экран (firewall) на уровне сервера;
— Регулярное обновление программного обеспечения;
— Ограничение частоты запросов (rate limiting) для предотвращения перебора.

7. ПРАВА СУБЪЕКТА ПЕРСОНАЛЬНЫХ ДАННЫХ

7.1. Вы имеете право:
— Получить информацию об обработке ваших персональных данных;
— Потребовать уточнения, блокирования или уничтожения персональных данных;
— Отозвать согласие на обработку персональных данных;
— Удалить свой аккаунт и все связанные данные;
— Получить свои данные в машиночитаемом формате (экспорт);
— Обжаловать действия Оператора в Роскомнадзор (https://rkn.gov.ru/).

7.2. Для реализации указанных прав вы можете:
— Удалить аккаунт через настройки профиля;
— Обратиться в поддержку: https://t.me/Dorof_hanzo или support@belvra.ru.

8. ПЕРЕДАЧА ДАННЫХ ТРЕТЬИМ ЛИЦАМ

8.1. Оператор не продаёт и не передаёт персональные данные третьим лицам для маркетинговых целей.

8.2. Данные передаются следующим третьим лицам исключительно для обеспечения работы Сервиса:

а) АО «Т-Банк» (Россия, лицензия ЦБ РФ) — обработка платежей за подписки. Передаются: сумма платежа, email. Данные банковских карт вводятся на защищённой странице Т-Банка.

б) Perplexity AI (США) — обработка текстовых ИИ-запросов. Передаются только данные, явно отправленные Пользователем для анализа. Данные не хранятся после обработки.

в) ООО «ЯНДЕКС» (Россия, ИНН 7736207543) — сервис Яндекс.Метрика для сбора анонимной статистики посещений; API Яндекс.Карт для отображения карт и геопоиска. При использовании карт IP-адрес и координаты передаются серверам Яндекса.

г) Cloudflare, Inc. (США) — защита от DDoS-атак и ускорение загрузки. Cloudflare обрабатывает IP-адреса и заголовки HTTP-запросов. Политика конфиденциальности: https://www.cloudflare.com/privacypolicy/

д) Google LLC (США) — Firebase Cloud Messaging для отправки push-уведомлений. Передаются: токен устройства, заголовок и текст уведомления. Персональные данные пользователя не передаются в Google.

е) Исполнение обязательств по договору: имя и контактные данные клиента передаются мастеру при записи на услугу.

ж) Требования законодательства РФ: по запросу уполномоченных государственных органов в порядке, установленном законом.

8.3. Трансграничная передача данных:
Персональные данные могут передаваться в США (Cloudflare, Google, Perplexity AI) на основании согласия субъекта (п. 1 ч. 4 ст. 12 ФЗ-152) и необходимости исполнения договора (п. 2 ч. 4 ст. 12 ФЗ-152). Указанные компании обеспечивают адекватный уровень защиты персональных данных.

9. ФАЙЛЫ COOKIE

9.1. Сервис использует следующие файлы cookie:
— Технические cookie (csrftoken, sessionid) — необходимы для работы аутентификации и защиты от CSRF-атак. Обязательные.
— Яндекс.Метрика (_ym_uid, _ym_d, _ym_isad, _ym_visorc) — сбор анонимной статистики посещений. Данные обрабатываются в деперсонализированном виде.
— Cloudflare (__cf_bm, cf_clearance) — защита от ботов и DDoS.

9.2. Вы можете отключить cookie в настройках браузера. При отключении технических cookie работа Сервиса может быть ограничена.

10. ИЗМЕНЕНИЯ В ПОЛИТИКЕ

10.1. Оператор вправе вносить изменения в настоящую Политику. Актуальная версия размещена в Сервисе с указанием даты вступления в силу.

10.2. При внесении существенных изменений пользователи уведомляются по электронной почте не менее чем за 7 дней до вступления изменений в силу.

10.3. Продолжение использования Сервиса после вступления изменений в силу означает согласие с обновлённой Политикой.
""".strip()
    }

    TERMS_OF_SERVICE = {
        "title": "Пользовательское соглашение",
        "version": "2.0",
        "effective_date": "2026-04-06",
        "content": """
1. ОБЩИЕ ПОЛОЖЕНИЯ

1.1. Настоящее Пользовательское соглашение (далее — Соглашение) регулирует отношения между администрацией сервиса Belvra (далее — Администрация) и пользователем сети Интернет (далее — Пользователь).

1.2. Сервис Belvra (далее — Сервис) — онлайн-платформа для записи на услуги в сфере красоты, связывающая клиентов и мастеров. Сервис является информационным посредником (ст. 1253.1 ГК РФ) и предоставляет платформу для связи клиентов и мастеров. Сервис НЕ является стороной сделки между клиентом и мастером.

1.3. Регистрируясь в Сервисе, Пользователь подтверждает, что ознакомился с настоящим Соглашением и принимает его условия в полном объёме.

1.4. Использование Сервиса допускается лицами, достигшими 18 лет.

1.5. Контактные данные Администрации:
— Telegram: https://t.me/Dorof_hanzo
— Email: support@belvra.ru

2. ПРЕДМЕТ СОГЛАШЕНИЯ

2.1. Администрация предоставляет Пользователю доступ к функционалу Сервиса на условиях, определённых настоящим Соглашением.

2.2. Сервис предоставляет следующие возможности:
— Для клиентов: поиск мастеров (текстовый, по карте, с AI), запись на услуги, управление записями, чат с мастерами, отзывы и рейтинги, избранные мастера;
— Для мастеров: управление профилем и расписанием, приём записей, портфолио работ, чат с клиентами, аналитика, заметки о клиентах, список дел.

2.3. Оплата услуг мастера осуществляется клиентом напрямую мастеру без участия Сервиса. Сервис обрабатывает только платежи за подписки PRO.

3. РЕГИСТРАЦИЯ И АККАУНТ

3.1. Для использования Сервиса необходима регистрация с указанием достоверных данных.

3.2. Пользователь обязуется не передавать данные своего аккаунта третьим лицам и самостоятельно обеспечивать конфиденциальность пароля.

3.3. Пользователь несёт ответственность за все действия, совершённые от имени его аккаунта, до момента уведомления Администрации о несанкционированном доступе. При обнаружении несанкционированного использования аккаунта Пользователь обязан незамедлительно сообщить об этом в поддержку: https://t.me/Dorof_hanzo.

3.4. Администрация вправе заблокировать или удалить аккаунт Пользователя по следующим основаниям:
— Нарушение условий настоящего Соглашения;
— Размещение противоправного, оскорбительного, порнографического, экстремистского или вредоносного контента;
— Использование Сервиса для мошеннических действий;
— Систематические жалобы от других Пользователей;
— Предоставление заведомо ложных данных при регистрации;
— Действия, направленные на нарушение работоспособности Сервиса;
— Размещение спама или рекламы сторонних сервисов;
— Нарушение авторских прав третьих лиц.
Администрация уведомляет Пользователя о блокировке с указанием причины по электронной почте. Пользователь вправе обжаловать решение о блокировке, обратившись в поддержку в течение 30 дней.

4. ПРАВА И ОБЯЗАННОСТИ ПОЛЬЗОВАТЕЛЯ

4.1. Пользователь имеет право:
— Использовать доступный функционал Сервиса;
— Получать техническую поддержку;
— Удалить свой аккаунт в любое время;
— Получить информацию о своих персональных данных;
— Экспортировать свои данные (при наличии подписки PRO).

4.2. Пользователь обязуется:
— Предоставлять достоверную информацию при регистрации;
— Не использовать Сервис для противоправных целей;
— Не размещать оскорбительный, незаконный или вредоносный контент;
— Соблюдать права других пользователей;
— Не предпринимать действия, направленные на нарушение работы Сервиса;
— Не использовать контактные данные, полученные через Сервис, для спам-рассылок.

5. ПРАВА И ОБЯЗАННОСТИ АДМИНИСТРАЦИИ

5.1. Администрация имеет право:
— Изменять функционал Сервиса с предварительным уведомлением Пользователей не менее чем за 7 дней до внесения существенных изменений; незначительные улучшения и исправления ошибок могут выполняться без предварительного уведомления;
— Приостановить доступ Пользователя при нарушении условий Соглашения с указанием причины;
— Направлять Пользователю служебные уведомления (email, push);
— Проводить плановые технические работы с предварительным уведомлением не менее чем за 24 часа;
— Удалить контент Пользователя (фото, отзывы, сообщения) без предупреждения если он нарушает п. 3.4 настоящего Соглашения.

5.2. Администрация обязуется:
— Обеспечивать работоспособность Сервиса;
— Защищать персональные данные Пользователей в соответствии с ФЗ-152;
— Рассматривать обращения Пользователей в срок не более 10 рабочих дней.

6. ПОДПИСКИ И ОПЛАТА

6.1. Доступ к расширенному функционалу предоставляется по платной подписке PRO (для мастеров и клиентов отдельно).

6.2. Стоимость подписки указана в Сервисе и может быть изменена с предварительным уведомлением не менее чем за 14 дней. Изменение цены не затрагивает текущий оплаченный период подписки.

6.3. Оплата производится через сертифицированного платёжного провайдера АО «Т-Банк» (лицензия ЦБ РФ). Данные банковских карт вводятся на защищённой странице провайдера и не проходят через серверы Сервиса.

6.4. Возврат средств за подписку:
— В течение 3 дней после оплаты — полный возврат;
— При недоступности Сервиса более 12 дней — пропорциональный возврат;
— При повторном списании из-за технического сбоя — полный возврат дублирующего платежа.
Для получения возврата обратитесь в поддержку: https://t.me/Dorof_hanzo или support@belvra.ru.

6.5. Программа Early Adopter:
— Пользователи, получившие статус Early Adopter, получают бесплатный пожизненный доступ к PRO-функционалу;
— Администрация вправе изменить условия программы для НОВЫХ участников, но не вправе отменить статус существующих Early Adopter.

6.6. Реферальная программа:
— Каждый пользователь получает уникальный реферальный код;
— При оформлении приглашённым пользователем подписки Pro пригласивший получает 1 месяц подписки Pro бесплатно;
— Реферальные вознаграждения суммируются;
— Администрация вправе изменить условия реферальной программы с предварительным уведомлением.

7. ИИ-ФУНКЦИИ

7.1. Сервис предоставляет вспомогательные функции на основе искусственного интеллекта: анализ фотографий, генерация текстовых описаний для портфолио, подсказки ответов в чате, интеллектуальный поиск мастеров.

7.2. Пользователь самостоятельно принимает решение об использовании ИИ-функций и определяет, какие данные отправлять для анализа. Анализ изображений выполняется локально на серверах Сервиса. Текстовые запросы обрабатываются с привлечением стороннего ИИ-провайдера (Perplexity AI) и не сохраняются после обработки.

7.3. Результаты ИИ-анализа формируются автоматически и носят исключительно рекомендательный характер. Администрация не гарантирует точность, полноту и применимость результатов. Пользователь использует результаты ИИ-анализа на своё усмотрение и под свою ответственность. Администрация не несёт ответственности за решения, принятые Пользователем на основе результатов ИИ-анализа.

8. ИНТЕЛЛЕКТУАЛЬНАЯ СОБСТВЕННОСТЬ

8.1. Все элементы Сервиса (дизайн, программный код, логотипы, название «Belvra») являются интеллектуальной собственностью Администрации и защищены законодательством РФ об авторском праве.

8.2. Контент, размещённый Пользователем (фотографии портфолио, описания, отзывы), остаётся собственностью Пользователя. Размещая контент, Пользователь предоставляет Администрации неисключительную безвозмездную лицензию на его отображение, хранение и передачу в рамках функционала Сервиса на весь срок размещения.

8.3. Пользователь гарантирует, что размещаемый контент не нарушает права третьих лиц. В случае получения претензий от третьих лиц ответственность несёт Пользователь, разместивший контент.

9. ОТВЕТСТВЕННОСТЬ

9.1. Сервис является информационным посредником. Администрация не несёт ответственности за:
— Качество услуг, оказываемых мастерами клиентам;
— Квалификацию, образование, сертификаты или лицензии мастеров;
— Споры между клиентами и мастерами;
— Вред здоровью, причинённый в результате оказания услуг мастером;
— Убытки, вызванные нарушением Пользователем условий Соглашения;
— Точность и результаты ИИ-анализа (см. раздел 7);
— Действия третьих лиц (платёжных провайдеров, ИИ-сервисов).

9.2. Администрация не проверяет квалификацию мастеров, наличие образования, сертификатов или лицензий. Мастер самостоятельно несёт ответственность за качество оказываемых услуг, соблюдение санитарных норм и требований законодательства.

9.3. Пользователь обязуется самостоятельно оценивать риски аллергических реакций и противопоказаний перед записью на процедуру. В случае причинения вреда здоровью претензии направляются мастеру, оказавшему услугу.

9.4. Совокупная ответственность Администрации перед Пользователем по любым претензиям, связанным с использованием Сервиса, ограничена суммой, уплаченной Пользователем за подписку за последние 12 месяцев.

9.5. Администрация обязуется реагировать на аварийные ситуации в течение 24 часов. В случае форс-мажора или масштабных технических работ Администрация вправе приостановить работу Сервиса на срок не более 12 дней. При превышении — Пользователь вправе потребовать пропорциональный возврат средств за подписку.

10. ОТЗЫВЫ

10.1. Отзыв можно оставить только после завершённой записи. Один отзыв на одну запись.

10.2. Администрация вправе удалить отзыв, содержащий нецензурную лексику, угрозы, персональные данные третьих лиц, заведомо ложные сведения или спам.

11. ОБРАБОТКА ПЕРСОНАЛЬНЫХ ДАННЫХ

11.1. Обработка персональных данных осуществляется в соответствии с Политикой конфиденциальности, которая является неотъемлемой частью настоящего Соглашения.

11.2. Регистрируясь, Пользователь даёт согласие на обработку персональных данных в соответствии с ФЗ-152, включая трансграничную передачу данных (см. раздел 8 Политики конфиденциальности).

12. РАЗРЕШЕНИЕ СПОРОВ

12.1. Все споры разрешаются путём переговоров. Досудебная претензия направляется на support@belvra.ru или через https://t.me/Dorof_hanzo. Срок рассмотрения претензии — 30 календарных дней.

12.2. В случае невозможности достижения соглашения споры рассматриваются в суде в соответствии с законодательством Российской Федерации.

13. ЗАКЛЮЧИТЕЛЬНЫЕ ПОЛОЖЕНИЯ

13.1. Настоящее Соглашение вступает в силу с момента регистрации Пользователя и действует бессрочно.

13.2. Администрация вправе вносить изменения в Соглашение с уведомлением Пользователей не менее чем за 7 дней по электронной почте.

13.3. Продолжение использования Сервиса после вступления изменений в силу означает принятие новых условий. В случае несогласия Пользователь вправе удалить аккаунт.

13.4. Настоящее Соглашение регулируется законодательством Российской Федерации.
""".strip()
    }

    def get(self, request):
        doc_type = request.query_params.get("type", "all")

        if doc_type == "privacy":
            return Response(self.PRIVACY_POLICY)
        elif doc_type == "terms":
            return Response(self.TERMS_OF_SERVICE)

        return Response({
            "privacy_policy": self.PRIVACY_POLICY,
            "terms_of_service": self.TERMS_OF_SERVICE,
        })


@extend_schema(
    tags=["Юридические документы"],
    summary="Отзыв согласия",
    description="Отзыв согласия на обработку персональных данных. После отзыва аккаунт будет деактивирован."
)
class WithdrawConsentView(APIView):
    """Withdraw consent for personal data processing (FZ-152 Article 9)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        consent_type = request.data.get("type")

        if consent_type == "privacy":
            user.privacy_accepted_at = None
            user.privacy_version_accepted = ""
            user.is_active = False
            user.save(update_fields=["privacy_accepted_at", "privacy_version_accepted", "is_active"])
            logout(request)
            return Response({
                "detail": "Согласие на обработку ПДн отозвано. Аккаунт деактивирован. Для восстановления обратитесь в поддержку."
            })
        elif consent_type == "terms":
            user.terms_accepted_at = None
            user.terms_version_accepted = ""
            user.is_active = False
            user.save(update_fields=["terms_accepted_at", "terms_version_accepted", "is_active"])
            logout(request)
            return Response({
                "detail": "Пользовательское соглашение отозвано. Аккаунт деактивирован."
            })

        return Response(
            {"detail": "Укажите type: privacy или terms"},
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(
    tags=["Юридические документы"],
    summary="Статус согласий",
    description="Получение текущего статуса согласий пользователя"
)
class ConsentStatusView(APIView):
    """Get current consent status for the authenticated user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        current_privacy_version = LegalDocumentsView.PRIVACY_POLICY["version"]
        current_terms_version = LegalDocumentsView.TERMS_OF_SERVICE["version"]

        return Response({
            "privacy": {
                "accepted": user.privacy_accepted_at is not None,
                "accepted_at": user.privacy_accepted_at,
                "version_accepted": user.privacy_version_accepted or None,
                "current_version": current_privacy_version,
                "needs_update": (
                    user.privacy_version_accepted != current_privacy_version
                    if user.privacy_accepted_at else True
                ),
            },
            "terms": {
                "accepted": user.terms_accepted_at is not None,
                "accepted_at": user.terms_accepted_at,
                "version_accepted": user.terms_version_accepted or None,
                "current_version": current_terms_version,
                "needs_update": (
                    user.terms_version_accepted != current_terms_version
                    if user.terms_accepted_at else True
                ),
            }
        })

    def post(self, request):
        """Re-accept updated legal documents."""
        user = request.user
        consent_type = request.data.get("type")
        now = timezone.now()

        if consent_type == "privacy":
            user.privacy_accepted_at = now
            user.privacy_version_accepted = LegalDocumentsView.PRIVACY_POLICY["version"]
            user.save(update_fields=["privacy_accepted_at", "privacy_version_accepted"])
            return Response({"detail": "Согласие на обработку ПДн обновлено"})
        elif consent_type == "terms":
            user.terms_accepted_at = now
            user.terms_version_accepted = LegalDocumentsView.TERMS_OF_SERVICE["version"]
            user.save(update_fields=["terms_accepted_at", "terms_version_accepted"])
            return Response({"detail": "Пользовательское соглашение принято"})
        elif consent_type == "all":
            user.privacy_accepted_at = now
            user.privacy_version_accepted = LegalDocumentsView.PRIVACY_POLICY["version"]
            user.terms_accepted_at = now
            user.terms_version_accepted = LegalDocumentsView.TERMS_OF_SERVICE["version"]
            user.save(update_fields=[
                "privacy_accepted_at", "privacy_version_accepted",
                "terms_accepted_at", "terms_version_accepted"
            ])
            return Response({"detail": "Все согласия обновлены"})

        return Response(
            {"detail": "Укажите type: privacy, terms или all"},
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema_view(
    list=extend_schema(
        tags=["Избранное"],
        summary="Список избранных мастеров",
        description="Получение списка избранных мастеров текущего пользователя"
    ),
    create=extend_schema(
        tags=["Избранное"],
        summary="Добавить в избранное",
        description="Добавить мастера в избранное"
    ),
    destroy=extend_schema(
        tags=["Избранное"],
        summary="Удалить из избранного",
        description="Удалить мастера из избранного"
    ),
)
class FavoriteMasterViewSet(viewsets.ModelViewSet):
    """ViewSet for favorite masters."""

    serializer_class = FavoriteMasterSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        return FavoriteMaster.objects.filter(
            user=self.request.user
        ).select_related("master__user")

    @extend_schema(
        tags=["Избранное"],
        summary="Проверить избранное",
        description="Проверить, находится ли мастер в избранном"
    )
    @action(detail=False, methods=["get"], url_path="check/(?P<master_id>[^/.]+)")
    def check(self, request, master_id=None):
        """Check if master is in favorites."""
        is_favorite = FavoriteMaster.objects.filter(
            user=request.user,
            master_id=master_id
        ).exists()
        return Response({"is_favorite": is_favorite})

    @extend_schema(
        tags=["Избранное"],
        summary="Переключить избранное",
        description="Добавить или удалить мастера из избранного"
    )
    @action(detail=False, methods=["post"], url_path="toggle/(?P<master_id>[^/.]+)")
    def toggle(self, request, master_id=None):
        """Toggle master favorite status."""
        try:
            master = MasterProfile.objects.get(id=master_id)
        except MasterProfile.DoesNotExist:
            return Response(
                {"detail": "Мастер не найден"},
                status=status.HTTP_404_NOT_FOUND
            )

        with transaction.atomic():
            favorite = FavoriteMaster.objects.select_for_update().filter(
                user=request.user,
                master=master
            ).first()

            if favorite:
                favorite.delete()
                return Response({
                    "is_favorite": False,
                    "detail": "Мастер удалён из избранного"
                })

            # Check favorites limit from subscription
            sub = getattr(request.user, "subscription", None)
            max_fav = sub.plan.max_favorites if (sub and sub.is_active) else 5
            if max_fav > 0:  # 0 = unlimited
                current = FavoriteMaster.objects.filter(user=request.user).count()
                if current >= max_fav:
                    return Response(
                        {"error": f"Лимит избранных мастеров ({max_fav}). Перейдите на PRO для безлимита."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            FavoriteMaster.objects.create(user=request.user, master=master)
            return Response({
                "is_favorite": True,
                "detail": "Мастер добавлен в избранное"
            }, status=status.HTTP_201_CREATED)


class BlockedListView(APIView):
    """List blocked users."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        blocked = BlockedUser.objects.filter(blocker=request.user).select_related("blocked")
        data = [
            {
                "id": str(b.id),
                "user_id": str(b.blocked.id),
                "name": b.blocked.full_name,
                "email": b.blocked.email,
                "reason": b.reason,
                "created_at": b.created_at.isoformat(),
            }
            for b in blocked
        ]
        return Response(data)


class BlockUserView(APIView):
    """Block/unblock a user."""
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        try:
            target = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)

        if target == request.user:
            return Response({"detail": "Нельзя заблокировать себя"}, status=status.HTTP_400_BAD_REQUEST)

        reason = request.data.get("reason", "")
        BlockedUser.objects.get_or_create(
            blocker=request.user, blocked=target,
            defaults={"reason": reason}
        )
        return Response({"detail": "Пользователь заблокирован"})

    def delete(self, request, user_id):
        BlockedUser.objects.filter(blocker=request.user, blocked_id=user_id).delete()
        return Response({"detail": "Пользователь разблокирован"})


class UserStatusView(APIView):
    """Get user online status."""
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "is_online": user.is_online,
            "last_seen": user.last_seen.isoformat() if user.last_seen else None,
        })
