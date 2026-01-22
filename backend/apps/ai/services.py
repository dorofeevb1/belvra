"""
AI service using Perplexity API for text and Ollama LLaVA for vision.
"""

import json
import logging
import re
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


class AIService:
    """Service for interacting with Perplexity AI and Ollama LLaVA."""

    def __init__(self):
        self.perplexity_api_key = getattr(settings, "PERPLEXITY_API_KEY", "")
        self.perplexity_model = "sonar"
        self.perplexity_url = "https://api.perplexity.ai/chat/completions"
        self.ollama_url = getattr(settings, "OLLAMA_URL", "http://localhost:11434")
        self.ollama_vision_model = "llava:7b"

    def _make_perplexity_request(self, messages: list[dict], max_tokens: int = 1024) -> dict | None:
        """Make a request to the Perplexity API."""
        import requests

        if not self.perplexity_api_key:
            logger.warning("Perplexity API key not configured")
            return None

        payload = {
            "model": self.perplexity_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }

        try:
            response = requests.post(
                self.perplexity_url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.perplexity_api_key}",
                    "Content-Type": "application/json"
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Perplexity API error: {e}")
            return None

    def _make_ollama_vision_request(self, image_base64: str, prompt: str) -> dict | None:
        """Make a vision request to Ollama API with LLaVA model."""
        import requests

        url = f"{self.ollama_url}/api/generate"

        payload = {
            "model": self.ollama_vision_model,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=120
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            return None

    def _extract_perplexity_text(self, response: dict) -> str:
        """Extract text from Perplexity response."""
        try:
            return response.get("choices", [{}])[0].get("message", {}).get("content", "")
        except (IndexError, KeyError):
            return ""

    def _extract_ollama_text(self, response: dict) -> str:
        """Extract text from Ollama response."""
        try:
            return response.get("response", "")
        except (KeyError):
            return ""

    def _extract_json(self, text: str) -> dict | None:
        """Extract JSON from response text."""
        try:
            # Try to find JSON in markdown code block first
            match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', text)
            if match:
                return json.loads(match.group(1))
            # Otherwise try to find raw JSON
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
        return None

    def generate_portfolio_content(self, image_base64: str) -> dict[str, Any]:
        """
        Generate description and hashtags for a portfolio image using Ollama LLaVA.

        Args:
            image_base64: Base64 encoded image data

        Returns:
            Dict with 'description' and 'hashtags' keys
        """
        prompt = """Проанализируй это изображение работы бьюти-мастера (маникюр, макияж, прическа, брови и т.д.).

Определи:
1. Какой тип работы изображён (маникюр, педикюр, макияж, причёска, брови, ресницы и т.д.)
2. Особенности работы (цвет, техника, стиль)
3. Качество исполнения

Сгенерируй профессиональное описание для портфолио мастера и релевантные хештеги.

Ответь СТРОГО в JSON формате без дополнительного текста:
{
  "description": "Профессиональное описание работы на русском языке (2-3 предложения, описывающие конкретно ЭТУ работу)",
  "hashtags": ["хештег1", "хештег2", "хештег3", "хештег4", "хештег5"]
}

Хештеги должны быть на русском языке, без символа #, релевантные именно этой работе."""

        response = self._make_ollama_vision_request(image_base64, prompt)

        if not response:
            return {"description": "", "hashtags": []}

        try:
            text = self._extract_ollama_text(response)
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

        messages = [
            {
                "role": "system",
                "content": "Ты - помощник бьюти-мастера. Помогаешь составлять короткие профессиональные ответы клиентам."
            },
            {
                "role": "user",
                "content": f"""На основе истории переписки и последнего сообщения клиента, предложи 3 коротких варианта ответа.

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

        response = self._make_perplexity_request(messages)

        if not response:
            return []

        try:
            text = self._extract_perplexity_text(response)
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

        messages = [
            {
                "role": "system",
                "content": "Ты - поисковая система для бьюти-услуг. Анализируешь запросы пользователей и ранжируешь мастеров по релевантности."
            },
            {
                "role": "user",
                "content": f"""Пользователь ищет мастера по запросу: "{query}"

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

        response = self._make_perplexity_request(messages)

        if not response:
            return [str(m.get("id", "")) for m in masters]

        try:
            text = self._extract_perplexity_text(response)
            parsed = self._extract_json(text)
            if parsed:
                return parsed.get("masterIds", [])
        except Exception as e:
            logger.error(f"Error parsing master search: {e}")

        return [str(m.get("id", "")) for m in masters]


# Alias for backward compatibility
GeminiService = AIService
