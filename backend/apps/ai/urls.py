from django.urls import path

from .views import (
    AISearchMastersView,
    GenerateChatSuggestionsView,
    GeneratePortfolioContentView,
)

urlpatterns = [
    path("portfolio-content/", GeneratePortfolioContentView.as_view(), name="ai-portfolio-content"),
    path("chat-suggestions/", GenerateChatSuggestionsView.as_view(), name="ai-chat-suggestions"),
    path("search-masters/", AISearchMastersView.as_view(), name="ai-search-masters"),
]
