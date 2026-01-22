"""
API views for AI services.
"""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import GeminiService


class AnalyzePhotoView(APIView):
    """Analyze photo using AI vision model."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["ИИ"],
        summary="Анализ фотографии",
        description="Комплексный анализ изображения с помощью ИИ. Типы анализа: general, style, quality, recommendation",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "image_base64": {
                        "type": "string",
                        "description": "Base64 encoded image"
                    },
                    "analysis_type": {
                        "type": "string",
                        "enum": ["general", "style", "quality", "recommendation"],
                        "description": "Тип анализа: general (общий), style (стиль/тренды), quality (качество работы), recommendation (рекомендации)"
                    }
                },
                "required": ["image_base64"]
            }
        },
        responses={
            200: {
                "type": "object",
                "description": "Результат анализа зависит от типа"
            }
        }
    )
    def post(self, request):
        """Analyze photo with specified analysis type."""
        image_base64 = request.data.get("image_base64", "")
        analysis_type = request.data.get("analysis_type", "general")

        if not image_base64:
            return Response(
                {"error": "image_base64 is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        valid_types = ["general", "style", "quality", "recommendation"]
        if analysis_type not in valid_types:
            return Response(
                {"error": f"analysis_type must be one of: {', '.join(valid_types)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Remove data URL prefix if present
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]

        service = GeminiService()
        result = service.analyze_photo(image_base64, analysis_type)

        return Response(result)


class GeneratePortfolioContentView(APIView):
    """Generate portfolio content using AI."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["ИИ"],
        summary="Генерация контента для портфолио",
        description="Анализирует изображение и генерирует описание и хештеги",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "image_base64": {
                        "type": "string",
                        "description": "Base64 encoded image"
                    }
                },
                "required": ["image_base64"]
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "hashtags": {"type": "array", "items": {"type": "string"}}
                }
            }
        }
    )
    def post(self, request):
        """Generate description and hashtags from image."""
        image_base64 = request.data.get("image_base64", "")

        if not image_base64:
            return Response(
                {"error": "image_base64 is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Remove data URL prefix if present
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]

        service = GeminiService()
        result = service.generate_portfolio_content(image_base64)

        return Response(result)


class GenerateChatSuggestionsView(APIView):
    """Generate chat reply suggestions using AI."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["ИИ"],
        summary="Генерация вариантов ответа",
        description="Анализирует историю чата и предлагает варианты ответа мастеру",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "chat_history": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string"},
                                "content": {"type": "string"}
                            }
                        }
                    },
                    "last_client_message": {"type": "string"}
                },
                "required": ["last_client_message"]
            }
        },
        responses={
            200: {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "text": {"type": "string"}
                    }
                }
            }
        }
    )
    def post(self, request):
        """Generate chat suggestions."""
        chat_history = request.data.get("chat_history", [])
        last_client_message = request.data.get("last_client_message", "")

        if not last_client_message:
            return Response(
                {"error": "last_client_message is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = GeminiService()
        suggestions = service.generate_chat_suggestions(chat_history, last_client_message)

        return Response(suggestions)


class AISearchMastersView(APIView):
    """Search masters using AI-powered natural language query."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["ИИ"],
        summary="ИИ-поиск мастеров",
        description="Поиск мастеров по естественному запросу с ИИ-ранжированием",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "masters": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "name": {"type": "string"},
                                "specialization": {"type": "string"},
                                "address": {"type": "string"},
                                "rating": {"type": "number"},
                                "description": {"type": "string"}
                            }
                        }
                    }
                },
                "required": ["query", "masters"]
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "master_ids": {"type": "array", "items": {"type": "string"}}
                }
            }
        }
    )
    def post(self, request):
        """Search and rank masters by relevance."""
        query = request.data.get("query", "")
        masters = request.data.get("masters", [])

        if not query:
            return Response(
                {"error": "query is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = GeminiService()
        master_ids = service.search_masters(query, masters)

        return Response({"master_ids": master_ids})
