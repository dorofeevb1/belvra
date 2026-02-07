import math
import random
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import logout
from django.core.cache import cache
from django.db import transaction
from django.db.models import F, FloatField, Value
from django.db.models.functions import ACos, Cos, Radians, Sin
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.tasks import (
    send_email_verification_code_task,
    send_password_reset_email_task,
    send_welcome_email_task,
)

from .models import FavoriteMaster, MasterProfile, User
from .serializers import (
    ChangePasswordSerializer,
    EmailVerificationSerializer,
    FavoriteMasterSerializer,
    LoginSerializer,
    MasterProfileSerializer,
    MasterWithDistanceSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    TokenSerializer,
    UserCreateSerializer,
    UserSerializer,
)


class LoginRateThrottle(ScopedRateThrottle):
    scope = "login"


class RegisterRateThrottle(ScopedRateThrottle):
    scope = "register"


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
    throttle_classes = [RegisterRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate 6-digit verification code
        code = f"{random.randint(100000, 999999)}"
        cache_key = f"email_verify_code_{user.id}"
        cache.set(cache_key, code, timeout=600)  # 10 minutes

        # Send verification code via email
        send_email_verification_code_task.delay(str(user.id), code)

        token_data = TokenSerializer.get_token(user)
        return Response({
            **token_data,
            "verification_email": user.email,
        }, status=status.HTTP_201_CREATED)


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
    throttle_classes = [LoginRateThrottle]

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
            pass
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
    description="Получение списка всех доступных мастеров"
)
class MasterListView(generics.ListAPIView):
    """List all available masters."""

    serializer_class = MasterProfileSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return MasterProfile.objects.filter(
            is_available=True,
            user__is_active=True
        ).select_related("user")


@extend_schema(
    tags=["Мастера"],
    summary="Информация о мастере",
    description="Получение детальной информации о мастере"
)
class MasterDetailView(generics.RetrieveAPIView):
    """Retrieve master details."""

    queryset = MasterProfile.objects.select_related("user")
    serializer_class = MasterProfileSerializer
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

    serializer_class = MasterWithDistanceSerializer
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

        queryset = queryset.annotate(
            distance_km=Value(self.EARTH_RADIUS_KM) * ACos(
                Sin(Value(lat_rad)) * Sin(Radians(F("latitude"))) +
                Cos(Value(lat_rad)) * Cos(Radians(F("latitude"))) *
                Cos(Radians(F("longitude")) - Value(lng_rad)),
                output_field=FloatField()
            )
        ).filter(
            distance_km__lte=radius_km
        ).order_by("distance_km")

        return queryset


@extend_schema(
    tags=["Аутентификация"],
    summary="Запрос сброса пароля",
    description="Отправка email со ссылкой для сброса пароля"
)
class PasswordResetRequestView(APIView):
    """Request password reset - sends email with reset link."""

    permission_classes = [AllowAny]

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
            pass

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


@extend_schema(
    tags=["Аутентификация"],
    summary="Подтверждение email",
    description="Подтверждение email адреса с использованием токена"
)
class VerifyEmailView(APIView):
    """Verify email address with 6-digit code."""

    permission_classes = [AllowAny]

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
        code = f"{random.randint(100000, 999999)}"
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

            FavoriteMaster.objects.create(user=request.user, master=master)
            return Response({
                "is_favorite": True,
                "detail": "Мастер добавлен в избранное"
            }, status=status.HTTP_201_CREATED)
