"""URL: /api/v1/auth/..."""
from django.urls import path

from ..api.auth_views import (
    ChangePasswordView,
    ForgotPasswordView,
    LoginView,
    LogoutView,
    MeView,
    RefreshView,
    ResetPasswordView,
)

urlpatterns = [
    path("login", LoginView.as_view(), name="auth-login"),
    path("refresh", RefreshView.as_view(), name="auth-refresh"),
    path("logout", LogoutView.as_view(), name="auth-logout"),
    path("me", MeView.as_view(), name="auth-me"),
    path("change-password", ChangePasswordView.as_view(), name="auth-change-password"),
    path("forgot-password", ForgotPasswordView.as_view(), name="auth-forgot"),
    path("reset-password", ResetPasswordView.as_view(), name="auth-reset"),
]
