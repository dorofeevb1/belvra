"""Custom encrypted model fields using Fernet symmetric encryption."""

import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _get_fernet():
    key = getattr(settings, "FIELD_ENCRYPTION_KEY", None)
    if not key:
        raise ValueError(
            "settings.FIELD_ENCRYPTION_KEY is not set. "
            "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


class EncryptedCharField(models.TextField):
    """CharField that stores data encrypted at rest using Fernet.

    The value is transparently encrypted on save and decrypted on read.
    Cannot be used in filter()/exclude() — use a hash companion field for lookups.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("blank", True)
        kwargs.setdefault("default", "")
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value):
        if not value:
            return ""
        f = _get_fernet()
        return f.encrypt(value.encode()).decode()

    def from_db_value(self, value, expression, connection):
        if not value:
            return ""
        try:
            f = _get_fernet()
            return f.decrypt(value.encode()).decode()
        except (InvalidToken, Exception):
            return value  # fallback: return raw if decryption fails (migration period)

    def to_python(self, value):
        return value


def compute_hash(value: str) -> str:
    """Compute SHA-256 hash for lookup purposes."""
    if not value:
        return ""
    return hashlib.sha256(value.encode()).hexdigest()
