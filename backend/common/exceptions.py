"""Custom exception handler — format error konsisten {error: {code, message, details}}."""
from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class DomainError(exceptions.APIException):
    """Base untuk error domain RASMARA.

    Subclass: ScopeLockedError, InvalidStateTransitionError, dst.
    """

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Permintaan tidak dapat diproses."
    default_code = "DOMAIN_ERROR"

    def __init__(self, detail: str | None = None, code: str | None = None, status_code: int | None = None) -> None:
        super().__init__(detail=detail, code=code)
        if status_code is not None:
            self.status_code = status_code


class ScopeLockedError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Operasi terkunci karena BOQ revisi aktif sudah APPROVED. Lakukan perubahan via Addendum."
    default_code = "SCOPE_LOCKED"


class InvalidStateTransitionError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Transisi status tidak valid."
    default_code = "INVALID_STATE_TRANSITION"


def rasmara_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """Bungkus error DRF jadi format {error: {code, message, details}}."""
    if isinstance(exc, Http404):
        return _wrap("NOT_FOUND", "Sumber daya tidak ditemukan.", status.HTTP_404_NOT_FOUND)
    if isinstance(exc, DjangoPermissionDenied):
        return _wrap("PERMISSION_DENIED", str(exc) or "Tidak diizinkan.", status.HTTP_403_FORBIDDEN)

    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    code = "ERROR"
    message = "Terjadi kesalahan."
    details: Any = None

    if isinstance(exc, exceptions.APIException):
        code = getattr(exc, "default_code", code)
        if isinstance(exc.detail, dict):
            message = "Validasi gagal."
            details = exc.detail
        elif isinstance(exc.detail, list):
            message = "Validasi gagal."
            details = exc.detail
        else:
            message = str(exc.detail)
            # cek detail error code dari DRF
            if hasattr(exc.detail, "code"):
                code = str(exc.detail.code)

    response.data = {"error": {"code": code, "message": message, "details": details}}
    return response


def _wrap(code: str, message: str, http_status: int, details: Any = None) -> Response:
    return Response(
        {"error": {"code": code, "message": message, "details": details}},
        status=http_status,
    )
