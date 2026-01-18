"""
AI service using Google Gemini API.
"""

import base64
import json
import logging
import re
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


class GeminiService:
    """Service for interacting with Google Gemini AI."""

    def __init__(self):
        self.api_key = getattr(settings, "GEMINI_API_KEY", "")
        self.model = "gemini-2.0-flash"
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    def _make_request(self, contents: list[dict]) -> dict | None:
        """Make a request to the Gemini API."""
        import requests

        if not self.api_key:
            logger.warning("Gemini API key not configured")
            return None

        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1024,
            }
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return None

    def _extract_json(self, text: str) -> dict | None:
        """Extract JSON from response text."""
        try:
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
        return None

    def generate_portfolio_content(self, image_base64: str) -> dict[str, Any]:
        """
        Generate description and hashtags for a portfolio image.

        Args:
            image_base64: Base64 encoded image data

        Returns:
            Dict with 'description' and 'hashtags' keys
        """
        contents = [
            {
                "role": "user",
                "parts": [
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": image_base64
                        }
                    },
                    {
                        "text": """Ты - эксперт в бьюти-индустрии. Проанализируй это изображение работы бьюти-мастера.

Ответь строго в JSON формате:
{
  "description": "Профессиональное описание работы на русском языке (2-3 предложения)",
  "hashtags": ["хештег1", "хештег2", "хештег3", "хештег4", "хештег5"]
}

Хештеги должны быть релевантными, на русском языке, без символа #."""
                    }
                ]
            }
        ]

        response = self._make_request(contents)

        if not response:
            return {"description": "", "hashtags": []}

        try:
            text = response.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            parsed = self._extract_json(text)
            if parsed:
                return {
                    "description": parsed.get("description", ""),
                    "hashtags": parsed.get("hashtags", [])
                }
        except Exception as e:
            logger.error(f"Error parsing portfolio content: {e}")

        return {"description": "", "hashtags": []}

    def generate_chat_suggestions(
        self,
        chat_history: list[dict],
        last_client_message: str
    ) -> list[dict]:
        """
        Generate chat reply suggestions for a master.

        Args:
            chat_history: List of dicts with 'role' and 'content'
            last_client_message: The last message from the client

        Returns:
            List of suggestion dicts with 'id' and 'text'
        """
        history_text = "\n".join(
            f"{'Мастер' if m.get('role') == 'master' else 'Клиент'}: {m.get('content', '')}"
            for m in chat_history[-10:]
        )

        contents = [
            {
                "role": "user",
                "parts": [
                    {
                        "text": f"""Ты - помощник бьюти-мастера. На основе истории переписки и последнего сообщения клиента, предложи 3 коротких варианта ответа.

История переписки:
{history_text}

Последнее сообщение клиента: "{last_client_message}"

Ответь строго в JSON формате:
{{
  "suggestions": [
    "Короткий ответ 1 (до 50 символов)",
    "Короткий ответ 2 (до 50 символов)",
    "Короткий ответ 3 (до 50 символов)"
  ]
}}

Ответы должны быть вежливыми, профессиональными и уместными для бьюти-сферы."""
                    }
                ]
            }
        ]

        response = self._make_request(contents)

        if not response:
            return []

        try:
            text = response.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            parsed = self._extract_json(text)
            if parsed:
                suggestions = parsed.get("suggestions", [])
                return [
                    {"id": f"suggestion-{i}", "text": s}
                    for i, s in enumerate(suggestions)
                ]
        except Exception as e:
            logger.error(f"Error parsing chat suggestions: {e}")

        return []

    def search_masters(
        self,
        query: str,
        masters: list[dict]
    ) -> list[str]:
        """
        Search and rank masters based on a natural language query.

        Args:
            query: User's search query
            masters: List of master dicts with id, name, specialization, etc.

        Returns:
            List of master IDs sorted by relevance
        """
        masters_info = [
            {
                "id": str(m.get("id", "")),
                "name": m.get("name", ""),
                "specialization": m.get("specialization", ""),
                "address": m.get("address", ""),
                "rating": m.get("rating", 0),
                "description": m.get("description", "")
            }
            for m in masters
        ]

        contents = [
            {
                "role": "user",
                "parts": [
                    {
                        "text": f"""Ты - поисковая система для бьюти-услуг. Пользователь ищет мастера по запросу.

Запрос пользователя: "{query}"

Список доступных мастеров:
{json.dumps(masters_info, ensure_ascii=False, indent=2)}

Проанализируй запрос и верни отсортированный по релевантности список ID мастеров.

Ответь строго в JSON формате:
{{
  "masterIds": ["id1", "id2", ...]
}}

Если ни один мастер не подходит, верни пустой массив."""
                    }
                ]
            }
        ]

        response = self._make_request(contents)

        if not response:
            return [str(m.get("id", "")) for m in masters]

        try:
            text = response.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            parsed = self._extract_json(text)
            if parsed:
                return parsed.get("masterIds", [])
        except Exception as e:
            logger.error(f"Error parsing master search: {e}")

        return [str(m.get("id", "")) for m in masters]
