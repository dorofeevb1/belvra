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
        self.ollama_vision_model = "moondream:1.8b-v2-q4_K_M"

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
                timeout=300
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

    def analyze_photo(self, image_base64: str, analysis_type: str = "general") -> dict[str, Any]:
        """
        Perform comprehensive photo analysis using Ollama LLaVA.

        Args:
            image_base64: Base64 encoded image data
            analysis_type: Type of analysis - "general", "style", "quality", "recommendation"

        Returns:
            Dict with analysis results
        """
        prompts = {
            "general": """Проанализируй это изображение, связанное с бьюти-индустрией.

Определи и опиши:
1. Что изображено на фото (тип услуги, работа мастера, лицо клиента и т.д.)
2. Детальное описание того, что ты видишь
3. Ключевые особенности и детали
4. Качество фотографии

Ответь СТРОГО в JSON формате:
{
  "type": "тип изображения (маникюр/макияж/прическа/лицо/другое)",
  "description": "Подробное описание на русском языке (3-5 предложений)",
  "details": ["деталь1", "деталь2", "деталь3"],
  "colors": ["цвет1", "цвет2"],
  "photo_quality": "отличное/хорошее/среднее/плохое",
  "confidence": 0.0-1.0
}""",
            "style": """Проанализируй стиль и тренды на этом бьюти-изображении.

Определи:
1. Текущий стиль (классика, модерн, авангард и т.д.)
2. Актуальные тренды, которые использованы
3. Целевую аудиторию
4. Подходящие случаи для такого образа

Ответь СТРОГО в JSON формате:
{
  "style": "название стиля",
  "trends": ["тренд1", "тренд2"],
  "target_audience": "описание целевой аудитории",
  "occasions": ["повседневный", "вечерний", "свадебный", "деловой"],
  "season": "весна/лето/осень/зима/универсальный",
  "similar_styles": ["похожий стиль 1", "похожий стиль 2"]
}""",
            "quality": """Оцени качество работы бьюти-мастера на этом изображении.

Проанализируй:
1. Техническое исполнение
2. Аккуратность работы
3. Соответствие трендам
4. Общее впечатление

Ответь СТРОГО в JSON формате:
{
  "overall_score": 1-10,
  "technical_score": 1-10,
  "creativity_score": 1-10,
  "cleanliness_score": 1-10,
  "strengths": ["сильная сторона 1", "сильная сторона 2"],
  "improvements": ["что можно улучшить 1", "что можно улучшить 2"],
  "professional_level": "начинающий/средний/профессионал/эксперт",
  "feedback": "Общий отзыв о работе на русском языке"
}""",
            "recommendation": """На основе этого изображения (лицо/внешность клиента или текущий образ), предложи рекомендации по бьюти-услугам.

Определи:
1. Тип внешности/лица
2. Подходящие услуги и стили
3. Цветовую палитру
4. Рекомендации по уходу

Ответь СТРОГО в JSON формате:
{
  "face_shape": "форма лица если видно (овал/круг/квадрат/сердце/прямоугольник)",
  "skin_tone": "тон кожи если видно",
  "recommended_services": [
    {"service": "название услуги", "reason": "почему подходит"}
  ],
  "color_palette": ["подходящий цвет 1", "подходящий цвет 2"],
  "style_recommendations": ["рекомендация 1", "рекомендация 2"],
  "care_tips": ["совет по уходу 1", "совет по уходу 2"]
}"""
        }

        prompt = prompts.get(analysis_type, prompts["general"])
        response = self._make_ollama_vision_request(image_base64, prompt)

        if not response:
            return {"error": "Не удалось проанализировать изображение", "analysis_type": analysis_type}

        try:
            text = self._extract_ollama_text(response)
            parsed = self._extract_json(text)
            if parsed:
                parsed["analysis_type"] = analysis_type
                parsed["raw_response"] = text[:500] if len(text) > 500 else text
                return parsed
        except Exception as e:
            logger.error(f"Error parsing photo analysis: {e}")

        return {
            "error": "Не удалось распарсить ответ",
            "analysis_type": analysis_type,
            "raw_response": self._extract_ollama_text(response) if response else ""
        }

    def generate_portfolio_content(self, image_base64: str) -> dict[str, Any]:
        """
        Generate description and hashtags for a portfolio image using Ollama LLaVA.

        Args:
            image_base64: Base64 encoded image data

        Returns:
            Dict with 'description' and 'hashtags' keys
        """
        prompt = """Describe this beauty work image (manicure, makeup, hairstyle, etc).

Return JSON only:
{"description": "2-3 sentences about this work in Russian", "hashtags": ["tag1", "tag2", "tag3"]}"""

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
