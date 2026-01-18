"""
Django staging settings.
"""

from .production import *

# Staging-specific overrides
SECURE_SSL_REDIRECT = False
