import logging
import math
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

logger = logging.getLogger(__name__)


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

        # Grant early adopter Pro subscription (first 50 users)
        if user.is_early_adopter:
            self._grant_early_adopter_pro(user)

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
        ).select_related("user", "user__subscription", "user__subscription__plan")


@extend_schema(
    tags=["Мастера"],
    summary="Информация о мастере",
    description="Получение детальной информации о мастере"
)
class MasterDetailView(generics.RetrieveAPIView):
    """Retrieve master details."""

    queryset = MasterProfile.objects.select_related("user", "user__subscription", "user__subscription__plan")
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
        "version": "1.1",
        "effective_date": "2025-01-01",
        "content": """
1. ОБЩИЕ ПОЛОЖЕНИЯ

1.1. Настоящая Политика конфиденциальности (далее — Политика) определяет порядок обработки и защиты персональных данных пользователей сервиса Belvra (далее — Сервис).

1.2. Оператором персональных данных является администрация Сервиса (далее — Оператор).

1.3. Политика разработана в соответствии с Федеральным законом от 27.07.2006 № 152-ФЗ «О персональных данных».

2. ПЕРСОНАЛЬНЫЕ ДАННЫЕ, КОТОРЫЕ МЫ СОБИРАЕМ

2.1. При регистрации и использовании Сервиса мы собираем следующие персональные данные:
— Фамилия, имя;
— Адрес электронной почты (email);
— Номер телефона (при указании);
— Фотография профиля (при загрузке);
— Адрес оказания услуг (для мастеров);
— Геолокация (при использовании поиска мастеров поблизости);
— Данные о записях на услуги;
— Переписка в чате Сервиса.

2.2. В рамках реферальной программы мы собираем:
— Уникальный реферальный код пользователя;
— Информацию о том, кто пригласил пользователя;
— Статус и дату применения реферального вознаграждения.

2.3. При использовании AI-функций Сервиса (анализ фото, рекомендации, генерация описаний) данные могут обрабатываться с использованием технологий машинного обучения. Изображения и текстовые данные, переданные для AI-анализа, не хранятся после обработки.

2.4. В рамках портфолио мастера мы собираем:
— Фотографии работ;
— Описания и хештеги к работам;
— Данные о лайках и просмотрах.

2.5. Мы не собираем и не храним данные банковских карт. Платежи обрабатываются через сертифицированного платёжного провайдера (Т-Банк).

3. ЦЕЛИ ОБРАБОТКИ ПЕРСОНАЛЬНЫХ ДАННЫХ

3.1. Персональные данные обрабатываются для следующих целей:
— Регистрация и аутентификация пользователя;
— Предоставление основного функционала Сервиса (запись на услуги, управление расписанием, чат);
— Связь между клиентами и мастерами;
— Отправка уведомлений о записях, подтверждениях и напоминаниях;
— Обработка платежей и подписок;
— Функционирование реферальной программы;
— AI-анализ фотографий и генерация рекомендаций (по запросу пользователя);
— Улучшение качества Сервиса.

4. ПРАВОВЫЕ ОСНОВАНИЯ ОБРАБОТКИ

4.1. Обработка персональных данных осуществляется на основании:
— Согласия субъекта персональных данных (п. 1 ч. 1 ст. 6 ФЗ-152);
— Исполнения договора, стороной которого является субъект персональных данных (п. 5 ч. 1 ст. 6 ФЗ-152).

5. ХРАНЕНИЕ ПЕРСОНАЛЬНЫХ ДАННЫХ

5.1. Персональные данные хранятся на серверах, расположенных на территории Российской Федерации, в соответствии с ч. 5 ст. 18 ФЗ-152.

5.2. Персональные данные хранятся в течение всего срока использования Сервиса пользователем. При удалении аккаунта все персональные данные удаляются.

5.3. Данные о совершённых платежах хранятся в течение 3 лет после совершения операции в соответствии с требованиями законодательства.

6. ЗАЩИТА ПЕРСОНАЛЬНЫХ ДАННЫХ

6.1. Оператор принимает необходимые организационные и технические меры для защиты персональных данных:
— Шифрование паролей;
— Использование протокола HTTPS;
— Аутентификация с использованием JWT-токенов;
— Разграничение прав доступа;
— Регулярное обновление программного обеспечения.

7. ПРАВА СУБЪЕКТА ПЕРСОНАЛЬНЫХ ДАННЫХ

7.1. Вы имеете право:
— Получить информацию об обработке ваших персональных данных;
— Потребовать уточнения, блокирования или уничтожения персональных данных;
— Отозвать согласие на обработку персональных данных;
— Удалить свой аккаунт и все связанные данные;
— Обжаловать действия Оператора в Роскомнадзор.

7.2. Для реализации указанных прав вы можете:
— Удалить аккаунт через настройки профиля;
— Обратиться в службу поддержки.

8. ПЕРЕДАЧА ДАННЫХ ТРЕТЬИМ ЛИЦАМ

8.1. Оператор не продаёт и не передаёт персональные данные третьим лицам, за исключением случаев:
— Обработки платежей через платёжного провайдера (Т-Банк);
— Обработки AI-запросов через сторонние сервисы машинного обучения (при этом передаются только данные, явно отправленные пользователем для анализа; данные не сохраняются на серверах сторонних сервисов);
— Требований законодательства Российской Федерации.

9. ФАЙЛЫ COOKIE

9.1. Сервис использует технические файлы cookie, необходимые для работы аутентификации. Рекламные и аналитические cookie не используются.

10. ИЗМЕНЕНИЯ В ПОЛИТИКЕ

10.1. Оператор вправе вносить изменения в настоящую Политику. Актуальная версия размещена в Сервисе.

10.2. При внесении существенных изменений пользователи уведомляются по электронной почте.
""".strip()
    }

    TERMS_OF_SERVICE = {
        "title": "Пользовательское соглашение",
        "version": "1.1",
        "effective_date": "2025-01-01",
        "content": """
1. ОБЩИЕ ПОЛОЖЕНИЯ

1.1. Настоящее Пользовательское соглашение (далее — Соглашение) регулирует отношения между администрацией сервиса Belvra (далее — Администрация) и пользователем сети Интернет (далее — Пользователь).

1.2. Сервис Belvra (далее — Сервис) — онлайн-платформа для записи на услуги в сфере красоты, связывающая клиентов и мастеров.

1.3. Регистрируясь в Сервисе, Пользователь подтверждает, что ознакомился с настоящим Соглашением и принимает его условия в полном объёме.

1.4. Использование Сервиса допускается лицами, достигшими 18 лет.

2. ПРЕДМЕТ СОГЛАШЕНИЯ

2.1. Администрация предоставляет Пользователю доступ к функционалу Сервиса на условиях, определённых настоящим Соглашением.

2.2. Сервис предоставляет следующие возможности:
— Для клиентов: поиск мастеров, запись на услуги, управление записями, чат с мастерами, оплата услуг;
— Для мастеров: управление профилем и расписанием, приём записей, портфолио, чат с клиентами, приём платежей, аналитика.

3. РЕГИСТРАЦИЯ И АККАУНТ

3.1. Для использования Сервиса необходима регистрация с указанием достоверных данных.

3.2. Пользователь обязуется не передавать данные своего аккаунта третьим лицам.

3.3. Пользователь несёт ответственность за все действия, совершённые от имени его аккаунта.

3.4. Администрация вправе заблокировать или удалить аккаунт при нарушении настоящего Соглашения.

4. ПРАВА И ОБЯЗАННОСТИ ПОЛЬЗОВАТЕЛЯ

4.1. Пользователь имеет право:
— Использовать доступный функционал Сервиса;
— Получать техническую поддержку;
— Удалить свой аккаунт в любое время;
— Получить информацию о своих персональных данных.

4.2. Пользователь обязуется:
— Предоставлять достоверную информацию при регистрации;
— Не использовать Сервис для противоправных целей;
— Не размещать оскорбительный, незаконный или вредоносный контент;
— Соблюдать права других пользователей;
— Не предпринимать действия, направленные на нарушение работы Сервиса.

5. ПРАВА И ОБЯЗАННОСТИ АДМИНИСТРАЦИИ

5.1. Администрация имеет право:
— Изменять функционал Сервиса без предварительного уведомления;
— Приостановить доступ Пользователя при нарушении условий Соглашения;
— Направлять Пользователю служебные уведомления.

5.2. Администрация обязуется:
— Обеспечивать работоспособность Сервиса;
— Защищать персональные данные Пользователей в соответствии с ФЗ-152;
— Рассматривать обращения Пользователей.

6. ПОДПИСКИ И ОПЛАТА

6.1. Доступ к расширенному функционалу для мастеров предоставляется по платной подписке.

6.2. Стоимость подписки указана в Сервисе и может быть изменена с предварительным уведомлением.

6.3. Оплата производится через сертифицированного платёжного провайдера (Т-Банк).

6.4. Возврат средств за подписку осуществляется в соответствии с законодательством РФ о защите прав потребителей.

6.5. Первые 50 зарегистрированных пользователей получают бесплатную пожизненную подписку Pro (программа «Ранний пользователь»).

6.6. Реферальная программа:
— Каждый пользователь получает уникальный реферальный код;
— При регистрации нового пользователя по реферальному коду и оформлении им подписки Pro, пригласивший пользователь получает 1 месяц подписки Pro бесплатно;
— Реферальные вознаграждения суммируются (каждый приглашённый — дополнительный месяц);
— Администрация вправе изменить условия реферальной программы с предварительным уведомлением.

7. AI-ФУНКЦИИ

7.1. Сервис предоставляет AI-функции (анализ фото, генерация описаний, рекомендации по стилю).

7.2. При использовании AI-функций пользователь самостоятельно решает, какие данные отправлять для анализа.

7.3. Администрация не гарантирует точность результатов AI-анализа. Результаты носят рекомендательный характер.

8. ИНТЕЛЛЕКТУАЛЬНАЯ СОБСТВЕННОСТЬ

8.1. Все элементы Сервиса (дизайн, программный код, логотипы) являются интеллектуальной собственностью Администрации.

8.2. Контент, размещённый Пользователем (фотографии портфолио, описания), остаётся собственностью Пользователя. Размещая контент, Пользователь предоставляет Администрации неисключительную лицензию на его отображение в рамках Сервиса.

9. ОТВЕТСТВЕННОСТЬ

9.1. Администрация не несёт ответственности за:
— Качество услуг, оказываемых мастерами клиентам;
— Споры между клиентами и мастерами;
— Временную недоступность Сервиса по техническим причинам;
— Убытки, вызванные нарушением Пользователем условий Соглашения;
— Точность и результаты AI-анализа.

9.2. Сервис предоставляется «как есть». Администрация не гарантирует его бесперебойную работу.

10. ОБРАБОТКА ПЕРСОНАЛЬНЫХ ДАННЫХ

10.1. Обработка персональных данных осуществляется в соответствии с Политикой конфиденциальности, которая является неотъемлемой частью настоящего Соглашения.

10.2. Регистрируясь, Пользователь даёт согласие на обработку персональных данных в соответствии с ФЗ-152.

11. РАЗРЕШЕНИЕ СПОРОВ

11.1. Все споры разрешаются путём переговоров. В случае невозможности достижения соглашения — в суде по месту нахождения Администрации, в соответствии с законодательством РФ.

12. ЗАКЛЮЧИТЕЛЬНЫЕ ПОЛОЖЕНИЯ

12.1. Настоящее Соглашение вступает в силу с момента регистрации Пользователя и действует бессрочно.

12.2. Администрация вправе вносить изменения в Соглашение с уведомлением Пользователей.

12.3. Продолжение использования Сервиса после изменений означает принятие новых условий.
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

            FavoriteMaster.objects.create(user=request.user, master=master)
            return Response({
                "is_favorite": True,
                "detail": "Мастер добавлен в избранное"
            }, status=status.HTTP_201_CREATED)
