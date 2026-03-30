"""
URL configuration for Belvra project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # API v1
    path("api/v1/", include([
        path("auth/", include("apps.users.urls")),
        path("services/", include("apps.services.urls")),
        path("appointments/", include("apps.appointments.urls")),
        path("payments/", include("apps.payments.urls")),
        path("subscriptions/", include("apps.subscriptions.urls")),
        path("notifications/", include("apps.core.notification_urls")),
        path("chats/", include("apps.chat.urls")),
        path("todos/", include("apps.todo.urls")),
        path("ai/", include("apps.ai.urls")),
    ])),

    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # Health check
    path("health/", include("apps.core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Debug Toolbar (optional)
    try:
        import debug_toolbar
        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass
