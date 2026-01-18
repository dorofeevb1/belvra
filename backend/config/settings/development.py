"""
Django development settings.
"""

from .base import INSTALLED_APPS, MIDDLEWARE

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Debug Toolbar
INSTALLED_APPS = ["debug_toolbar"] + INSTALLED_APPS
MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE

INTERNAL_IPS = ["127.0.0.1", "localhost"]

# Email backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# CORS - allow all in development
CORS_ALLOW_ALL_ORIGINS = True

# Cache
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
