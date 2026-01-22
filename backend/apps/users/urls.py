from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    ChangePasswordView,
    FavoriteMasterViewSet,
    LoginView,
    LogoutView,
    MasterDetailView,
    MasterGeoSearchView,
    MasterListView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PasswordResetValidateTokenView,
    RegisterView,
    ResendVerificationEmailView,
    UploadAvatarView,
    UserProfileView,
    VerifyEmailView,
)

router = DefaultRouter()
router.register(r"favorites", FavoriteMasterViewSet, basename="favorite")

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("profile/", UserProfileView.as_view(), name="profile"),
    path("profile/avatar/", UploadAvatarView.as_view(), name="profile-avatar"),
    path("password/change/", ChangePasswordView.as_view(), name="change-password"),
    path("password/reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("password/reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("password/reset/validate/", PasswordResetValidateTokenView.as_view(), name="password-reset-validate"),
    path("email/verify/", VerifyEmailView.as_view(), name="email-verify"),
    path("email/resend-verification/", ResendVerificationEmailView.as_view(), name="email-resend-verification"),
    path("masters/", MasterListView.as_view(), name="master-list"),
    path("masters/nearby/", MasterGeoSearchView.as_view(), name="master-nearby"),
    path("masters/<uuid:pk>/", MasterDetailView.as_view(), name="master-detail"),
    path("", include(router.urls)),
]
