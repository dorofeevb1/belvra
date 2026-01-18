"""
Local development settings with SQLite.
"""

from .base import *

DEBUG = True

# Use SQLite for local development
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Disable email sending
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# CORS - allow all for development
CORS_ALLOW_ALL_ORIGINS = True
