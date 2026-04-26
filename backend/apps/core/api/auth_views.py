"""View untuk endpoint auth: login, refresh, logout, me, change-password, forgot, reset."""
import secrets
from datetime import datetime, timedelta, timezone

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.cache import cache
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    MeSerializer,
)

User = get_user_model()
token_gen = PasswordResetTokenGenerator()


class LoginView(TokenObtainPairView):
    """POST /api/v1/auth/login/  -> {access, refresh, user, must_change_password}"""

    serializer_class = LoginSerializer
    permission_classes = (AllowAny,)


class RefreshView(TokenRefreshView):
    """POST /api/v1/auth/refresh/  -> {access}"""

    permission_classes = (AllowAny,)


class LogoutView(APIView):
    """POST /api/v1/auth/logout/  body: {refresh}"""

    permission_classes = (IsAuthenticated,)

    def post(self, request) -> Response:
        token_str = request.data.get("refresh")
        if token_str:
            try:
                token = RefreshToken(token_str)
                token.blacklist()
            except Exception:  # noqa: BLE001
                pass
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """GET /api/v1/auth/me/  -> profil user + permission + menu tree."""

    permission_classes = (IsAuthenticated,)

    def get(self, request) -> Response:
        return Response(MeSerializer(request.user, context={"request": request}).data)


class ChangePasswordView(APIView):
    """POST /api/v1/auth/change-password/

    Body: {current_password?, new_password}
    Bila must_change_password=True, current_password tidak wajib (paksa ganti pertama).
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request) -> Response:
        s = ChangePasswordSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = request.user
        new_pwd = s.validated_data["new_password"]
        current = s.validated_data.get("current_password", "")

        if not user.must_change_password:
            if not user.check_password(current):
                return Response(
                    {"error": {"code": "WRONG_PASSWORD",
                               "message": "Password saat ini salah."}},
                    status=400,
                )

        user.set_password(new_pwd)
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password", "updated_at"])
        return Response({"detail": "Password berhasil diganti."})


class ForgotPasswordView(APIView):
    """POST /api/v1/auth/forgot-password/  body: {email}

    Selalu return 200 (jangan bocorkan ada/tidaknya email).
    """

    permission_classes = (AllowAny,)

    def post(self, request) -> Response:
        email = (request.data.get("email") or "").strip().lower()
        if not email:
            return Response({"detail": "Jika email terdaftar, tautan reset akan dikirim."})

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            uid = str(user.id)
            token = token_gen.make_token(user)
            cache.set(f"pwreset:{uid}:{token}", True, 60 * 30)  # 30 menit
            link = (request.build_absolute_uri("/").rstrip("/")
                    + f"/reset-password?uid={uid}&token={token}")
            send_mail(
                subject="Reset Password RASMARA",
                message=f"Klik tautan berikut untuk reset password (berlaku 30 menit):\n\n{link}\n\n"
                        f"Jika Anda tidak meminta, abaikan email ini.",
                from_email=None,
                recipient_list=[user.email],
                fail_silently=True,
            )
        return Response({"detail": "Jika email terdaftar, tautan reset akan dikirim."})


class ResetPasswordView(APIView):
    """POST /api/v1/auth/reset-password/ body: {uid, token, new_password}"""

    permission_classes = (AllowAny,)

    def post(self, request) -> Response:
        uid = request.data.get("uid")
        token = request.data.get("token")
        new_pwd = request.data.get("new_password")
        if not (uid and token and new_pwd):
            return Response(
                {"error": {"code": "VALIDATION_ERROR",
                           "message": "uid, token, new_password wajib."}},
                status=400,
            )
        if not cache.get(f"pwreset:{uid}:{token}"):
            return Response(
                {"error": {"code": "INVALID_TOKEN",
                           "message": "Token tidak valid atau sudah kadaluarsa."}},
                status=400,
            )
        try:
            user = User.objects.get(pk=uid, is_active=True)
        except User.DoesNotExist:
            return Response(
                {"error": {"code": "INVALID_TOKEN",
                           "message": "Token tidak valid."}},
                status=400,
            )
        if not token_gen.check_token(user, token):
            return Response(
                {"error": {"code": "INVALID_TOKEN",
                           "message": "Token tidak valid."}},
                status=400,
            )

        from django.contrib.auth.password_validation import validate_password
        try:
            validate_password(new_pwd, user=user)
        except Exception as e:  # noqa: BLE001
            return Response(
                {"error": {"code": "WEAK_PASSWORD", "message": str(e)}},
                status=400,
            )

        user.set_password(new_pwd)
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password", "updated_at"])
        cache.delete(f"pwreset:{uid}:{token}")
        return Response({"detail": "Password berhasil di-reset. Silakan login kembali."})
