"""
T-Bank (Tinkoff) e-acquiring API client.
"""

import hashlib
import hmac
import logging

import requests as http_requests
from django.conf import settings

logger = logging.getLogger(__name__)


class TBankService:
    """Low-level client for T-Bank (Tinkoff) e-acquiring API."""

    def __init__(self):
        self.terminal_key = settings.TBANK_TERMINAL_KEY
        self.password = settings.TBANK_PASSWORD
        self.api_url = getattr(settings, "TBANK_API_URL", "https://securepay.tinkoff.ru/v2/")
        self.test_mode = not self.terminal_key or not self.password

    def _generate_token(self, params: dict) -> str:
        """
        Generate Token for T-Bank API request.

        Algorithm:
        1. Collect all root-level scalar params (exclude nested objects/arrays).
        2. Add Password.
        3. Sort alphabetically by key.
        4. Concatenate values only.
        5. SHA-256 hash.
        """
        token_params = {}
        for key, value in params.items():
            if key == "Token":
                continue
            if isinstance(value, (dict, list)):
                continue
            token_params[key] = str(value)

        token_params["Password"] = self.password

        sorted_keys = sorted(token_params.keys())
        values_string = "".join(token_params[key] for key in sorted_keys)

        return hashlib.sha256(values_string.encode("utf-8")).hexdigest()

    def _request(self, method: str, params: dict) -> dict:
        """Make a request to T-Bank API."""
        params["TerminalKey"] = self.terminal_key
        params["Token"] = self._generate_token(params)

        url = f"{self.api_url}{method}"
        response = http_requests.post(url, json=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        if not data.get("Success", False):
            error_code = data.get("ErrorCode", "unknown")
            error_msg = data.get("Message", "") or data.get("Details", "")
            raise Exception(f"T-Bank API error {error_code}: {error_msg}")

        return data

    def verify_notification_token(self, params: dict) -> bool:
        """
        Verify T-Bank notification token.

        Same algorithm as _generate_token but applied to notification params.
        """
        received_token = params.get("Token", "")
        if not received_token:
            return False

        check_params = {}
        for key, value in params.items():
            if key == "Token":
                continue
            if isinstance(value, (dict, list)):
                continue
            check_params[key] = str(value)

        check_params["Password"] = self.password

        sorted_keys = sorted(check_params.keys())
        values_string = "".join(check_params[key] for key in sorted_keys)
        expected_token = hashlib.sha256(values_string.encode("utf-8")).hexdigest()

        return hmac.compare_digest(expected_token, received_token)
