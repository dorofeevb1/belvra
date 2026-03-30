"""
Django production settings.
"""

from environs import Env

env = Env()

DEBUG = False

# Trust X-Forwarded-Proto from nginx so build_absolute_uri returns https://
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Security
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=True)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=True)

# Email (configured via .env — Yandex SMTP: ssl on port 465)
EMAIL_BACKEND = env.str("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env.str("EMAIL_HOST", default="smtp.yandex.ru")
EMAIL_PORT = env.int("EMAIL_PORT", default=465)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=True)
EMAIL_HOST_USER = env.str("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env.str("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL", default="Belvra <noreply@belvra.ru>")
