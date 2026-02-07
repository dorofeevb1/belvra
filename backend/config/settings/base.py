"""
Django base settings for BeautyStyleService project.
"""

import os
from datetime import timedelta
from pathlib import Path

from environs import Env

env = Env()
env.read_env()

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Security
SECRET_KEY = env.str("DJANGO_SECRET_KEY", default="change-me-in-production")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=["http://localhost", "http://127.0.0.1", "http://37.77.104.201", "http://37.77.104.201:8080"])

# Application definition
DJANGO_APPS = [
    "unfold",  # Must be before django.contrib.admin
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "django_extensions",
    "drf_spectacular",
]

LOCAL_APPS = [
    "apps.core",
    "apps.users",
    "apps.services",
    "apps.appointments",
    "apps.payments",
    "apps.subscriptions",
    "apps.chat",
    "apps.todo",
    "apps.ai",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# Middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env.str("POSTGRES_DB", default="beautystyle"),
        "USER": env.str("POSTGRES_USER", default="postgres"),
        "PASSWORD": env.str("POSTGRES_PASSWORD", default="postgres"),
        "HOST": env.str("POSTGRES_HOST", default="localhost"),
        "PORT": env.int("POSTGRES_PORT", default=5432),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {
            "connect_timeout": 10,
        },
    }
}

# Cache (Redis)
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env.str("REDIS_URL", default="redis://localhost:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 50},
        },
        "KEY_PREFIX": "beautystyle",
    }
}

# Session
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Custom User Model
AUTH_USER_MODEL = "users.User"

# Internationalization
LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        "login": "10/minute",
        "register": "5/minute",
    },
}

# JWT Settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# CORS
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:4200", "http://127.0.0.1:4200"]
)
CORS_ALLOW_CREDENTIALS = True

# Celery
CELERY_BROKER_URL = env.str("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = env.str("CELERY_RESULT_BACKEND", default="redis://localhost:6379/2")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Celery Beat Schedule
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Appointment tasks
    "send-appointment-reminders": {
        "task": "apps.appointments.tasks.send_appointment_reminders",
        "schedule": crontab(hour=9, minute=0),  # Every day at 9:00
    },
    "mark-no-show-appointments": {
        "task": "apps.appointments.tasks.mark_no_show_appointments",
        "schedule": crontab(hour=0, minute=30),  # Every day at 00:30
    },
    "cleanup-old-appointments": {
        "task": "apps.appointments.tasks.cleanup_old_appointments",
        "schedule": crontab(hour=3, minute=0, day_of_week=0),  # Every Sunday at 3:00
    },
    "send-completion-reminder": {
        "task": "apps.appointments.tasks.send_completion_reminder",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
    },
    # Subscription tasks
    "check-expiring-subscriptions": {
        "task": "apps.subscriptions.tasks.check_expiring_subscriptions",
        "schedule": crontab(hour=10, minute=0),  # Every day at 10:00
    },
    "renew-subscriptions": {
        "task": "apps.subscriptions.tasks.renew_subscriptions",
        "schedule": crontab(hour=6, minute=0),  # Every day at 6:00
    },
    "expire-subscriptions": {
        "task": "apps.subscriptions.tasks.expire_subscriptions",
        "schedule": crontab(hour=1, minute=0),  # Every day at 1:00
    },
    "downgrade-to-free": {
        "task": "apps.subscriptions.tasks.downgrade_to_free",
        "schedule": crontab(hour=2, minute=0),  # Every day at 2:00
    },
    "reset-monthly-usage": {
        "task": "apps.subscriptions.tasks.reset_monthly_usage",
        "schedule": crontab(hour=0, minute=5, day_of_month=1),  # 1st of each month at 00:05
    },
    "notify-past-due-subscriptions": {
        "task": "apps.subscriptions.tasks.notify_past_due_subscriptions",
        "schedule": crontab(hour=11, minute=0),  # Every day at 11:00
    },
}

# API Documentation
SPECTACULAR_SETTINGS = {
    "TITLE": "BeautyStyle API",
    "DESCRIPTION": "API для сервиса записи в салоны красоты",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api/v1",
}

# YooKassa Payment Settings
YOOKASSA_SHOP_ID = env.str("YOOKASSA_SHOP_ID", default="")
YOOKASSA_SECRET_KEY = env.str("YOOKASSA_SECRET_KEY", default="")
YOOKASSA_WEBHOOK_SECRET = env.str("YOOKASSA_WEBHOOK_SECRET", default="")
YOOKASSA_SEND_RECEIPT = env.bool("YOOKASSA_SEND_RECEIPT", default=False)

# Payment Settings
PAYMENT_RETURN_URL = env.str("PAYMENT_RETURN_URL", default="http://localhost:4200/payment/success")
PLATFORM_COMMISSION_RATE = env.decimal("PLATFORM_COMMISSION_RATE", default="0.05")  # 5%
MIN_COMMISSION = env.decimal("MIN_COMMISSION", default="10.00")  # 10 RUB
PROVIDER_FEE_RATE = env.decimal("PROVIDER_FEE_RATE", default="0.02")  # ~2%
PAYMENT_HOLD_DAYS = env.int("PAYMENT_HOLD_DAYS", default=3)
PREPAYMENT_PERCENT = env.decimal("PREPAYMENT_PERCENT", default="0.20")  # 20%

# Withdrawal Settings
MIN_WITHDRAWAL_AMOUNT = env.decimal("MIN_WITHDRAWAL_AMOUNT", default="100.00")
MIN_AUTO_WITHDRAWAL_AMOUNT = env.decimal("MIN_AUTO_WITHDRAWAL_AMOUNT", default="1000.00")
WITHDRAWAL_FEES = {
    "card": {"fixed": env.decimal("WITHDRAWAL_FEE_CARD_FIXED", default="50.00"), "percent": env.decimal("WITHDRAWAL_FEE_CARD_PERCENT", default="0.00")},
    "yoomoney": {"fixed": env.decimal("WITHDRAWAL_FEE_YOOMONEY_FIXED", default="0.00"), "percent": env.decimal("WITHDRAWAL_FEE_YOOMONEY_PERCENT", default="0.03")},
    "bank_account": {"fixed": env.decimal("WITHDRAWAL_FEE_BANK_FIXED", default="0.00"), "percent": env.decimal("WITHDRAWAL_FEE_BANK_PERCENT", default="0.01")},
}

# Email Settings
EMAIL_BACKEND = env.str("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env.str("EMAIL_HOST", default="smtp.yandex.ru")
EMAIL_PORT = env.int("EMAIL_PORT", default=465)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=True)
EMAIL_HOST_USER = env.str("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env.str("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL", default="BeautyBook <noreply@beautybook.ru>")
SERVER_EMAIL = env.str("SERVER_EMAIL", default="errors@beautybook.ru")

# Frontend URL for email links
FRONTEND_URL = env.str("FRONTEND_URL", default="http://localhost:4200")

# AI Settings
PERPLEXITY_API_KEY = env.str("PERPLEXITY_API_KEY", default="")
OLLAMA_URL = env.str("OLLAMA_URL", default="http://localhost:11434")

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": env.str("DJANGO_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# Django Unfold Admin
UNFOLD = {
    "SITE_TITLE": "BeautyStyle Admin",
    "SITE_HEADER": "BeautyStyle",
    "SITE_SYMBOL": "spa",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "ENVIRONMENT": "config.settings.base.environment_callback",
    "COLORS": {
        "primary": {
            "50": "#fdf2f8",
            "100": "#fce7f3",
            "200": "#fbcfe8",
            "300": "#f9a8d4",
            "400": "#f472b6",
            "500": "#ec4899",
            "600": "#db2777",
            "700": "#be185d",
            "800": "#9d174d",
            "900": "#831843",
            "950": "#500724",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Навигация",
                "separator": True,
                "items": [
                    {
                        "title": "Главная",
                        "icon": "home",
                        "link": "/admin/",
                    },
                ],
            },
            {
                "title": "Пользователи",
                "separator": True,
                "items": [
                    {
                        "title": "Пользователи",
                        "icon": "people",
                        "link": "/admin/users/user/",
                    },
                    {
                        "title": "Профили мастеров",
                        "icon": "badge",
                        "link": "/admin/users/masterprofile/",
                    },
                ],
            },
            {
                "title": "Услуги",
                "separator": True,
                "items": [
                    {
                        "title": "Категории",
                        "icon": "category",
                        "link": "/admin/services/category/",
                    },
                    {
                        "title": "Услуги",
                        "icon": "spa",
                        "link": "/admin/services/service/",
                    },
                    {
                        "title": "Услуги мастеров",
                        "icon": "assignment",
                        "link": "/admin/services/masterservice/",
                    },
                ],
            },
            {
                "title": "Записи",
                "separator": True,
                "items": [
                    {
                        "title": "Записи",
                        "icon": "calendar_month",
                        "link": "/admin/appointments/appointment/",
                    },
                    {
                        "title": "Расписание",
                        "icon": "schedule",
                        "link": "/admin/appointments/workschedule/",
                    },
                    {
                        "title": "Отзывы",
                        "icon": "reviews",
                        "link": "/admin/appointments/review/",
                    },
                ],
            },
            {
                "title": "Платежи",
                "separator": True,
                "items": [
                    {
                        "title": "Платежи",
                        "icon": "payments",
                        "link": "/admin/payments/payment/",
                    },
                    {
                        "title": "Кошельки",
                        "icon": "account_balance_wallet",
                        "link": "/admin/payments/wallet/",
                    },
                    {
                        "title": "Выводы средств",
                        "icon": "currency_exchange",
                        "link": "/admin/payments/withdrawal/",
                    },
                    {
                        "title": "Реквизиты выплат",
                        "icon": "credit_card",
                        "link": "/admin/payments/payoutdestination/",
                    },
                ],
            },
            {
                "title": "Подписки",
                "separator": True,
                "items": [
                    {
                        "title": "Планы подписок",
                        "icon": "card_membership",
                        "link": "/admin/subscriptions/subscriptionplan/",
                    },
                    {
                        "title": "Подписки",
                        "icon": "subscriptions",
                        "link": "/admin/subscriptions/subscription/",
                    },
                    {
                        "title": "Платежи за подписки",
                        "icon": "receipt_long",
                        "link": "/admin/subscriptions/subscriptionpayment/",
                    },
                ],
            },
            {
                "title": "Коммуникации",
                "separator": True,
                "items": [
                    {
                        "title": "Чаты",
                        "icon": "chat",
                        "link": "/admin/chat/chat/",
                    },
                    {
                        "title": "Сообщения",
                        "icon": "message",
                        "link": "/admin/chat/chatmessage/",
                    },
                    {
                        "title": "Уведомления",
                        "icon": "notifications",
                        "link": "/admin/core/notification/",
                    },
                    {
                        "title": "Портфолио",
                        "icon": "photo_library",
                        "link": "/admin/services/portfolioitem/",
                    },
                    {
                        "title": "Задачи",
                        "icon": "checklist",
                        "link": "/admin/todo/todoitem/",
                    },
                ],
            },
        ],
    },
}


def environment_callback(request):
    """Return environment name for admin header."""
    if DEBUG:
        return ["Разработка", "warning"]
    return ["Продакшен", "success"]
