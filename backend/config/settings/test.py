"""
Django test settings.
"""

from .base import *  # noqa

DEBUG = False

# Use SQLite for tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Faster password hashing for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable cache
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Disable Celery — run tasks synchronously, no Redis needed
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = None
CELERY_TASK_STORE_ERRORS_EVEN_IF_IGNORED = False
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = False

# Disable Channels layer (no Redis needed)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

# Email
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
