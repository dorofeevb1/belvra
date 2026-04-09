from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    BecomeMasterView,
    BlockedListView,
    BlockUserView,
    ChangePasswordView,
    ConsentStatusView,
    DeleteAccountView,
    FavoriteMasterViewSet,
    LegalDocumentsView,
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
    SwitchRoleView,
    UploadAvatarView,
    UserProfileView,
    UserStatusView,
    VerifyEmailView,
    WithdrawConsentView,
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
    path("profile/switch-role/", SwitchRoleView.as_view(), name="switch-role"),
    path("profile/become-master/", BecomeMasterView.as_view(), name="become-master"),
    path("password/change/", ChangePasswordView.as_view(), name="change-password"),
    path("password/reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("password/reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("password/reset/validate/", PasswordResetValidateTokenView.as_view(), name="password-reset-validate"),
    path("email/verify/", VerifyEmailView.as_view(), name="email-verify"),
    path("email/resend-verification/", ResendVerificationEmailView.as_view(), name="email-resend-verification"),
    path("masters/", MasterListView.as_view(), name="master-list"),
    path("masters/nearby/", MasterGeoSearchView.as_view(), name="master-nearby"),
    path("masters/<uuid:pk>/", MasterDetailView.as_view(), name="master-detail"),
    path("profile/delete-account/", DeleteAccountView.as_view(), name="delete-account"),
    path("legal/", LegalDocumentsView.as_view(), name="legal-documents"),
    path("consent/status/", ConsentStatusView.as_view(), name="consent-status"),
    path("consent/withdraw/", WithdrawConsentView.as_view(), name="consent-withdraw"),
    path("blocked/", BlockedListView.as_view(), name="blocked-list"),
    path("users/<uuid:user_id>/block/", BlockUserView.as_view(), name="block-user"),
    path("users/<uuid:user_id>/status/", UserStatusView.as_view(), name="user-status"),
    path("", include(router.urls)),
]
