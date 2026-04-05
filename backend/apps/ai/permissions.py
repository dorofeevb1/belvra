"""
Permissions for AI features.
"""

from rest_framework.permissions import BasePermission


class HasAIAccess(BasePermission):
    """Only allow users with ai_assistant_enabled in their subscription plan."""

    message = "AI-ассистент доступен только на тарифе PRO"

    def has_permission(self, request, view):
        sub = getattr(request.user, "subscription", None)
        if sub is None:
            return False
        return sub.is_active and sub.plan.ai_assistant_enabled
