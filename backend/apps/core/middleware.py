"""Middleware untuk capture konteks audit (user, IP, UA) ke thread-local."""
import threading
from typing import Any

_local = threading.local()


def get_current_user() -> Any:
    return getattr(_local, "user", None)


def get_current_request() -> Any:
    return getattr(_local, "request", None)


def get_audit_context() -> dict[str, Any]:
    return {
        "user": get_current_user(),
        "ip_address": getattr(_local, "ip_address", None),
        "user_agent": getattr(_local, "user_agent", ""),
        "godmode_bypass": getattr(_local, "godmode_bypass", False),
        "unlock_reason": getattr(_local, "unlock_reason", ""),
    }


def set_godmode(active: bool, reason: str = "") -> None:
    _local.godmode_bypass = active
    _local.unlock_reason = reason


class AuditContextMiddleware:
    """Set thread-local agar signal audit bisa baca user/IP/UA."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.request = request
        _local.user = getattr(request, "user", None) if getattr(request, "user", None) and request.user.is_authenticated else None
        _local.ip_address = self._client_ip(request)
        _local.user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]
        _local.godmode_bypass = False
        _local.unlock_reason = ""
        try:
            return self.get_response(request)
        finally:
            for attr in ("request", "user", "ip_address", "user_agent",
                         "godmode_bypass", "unlock_reason"):
                if hasattr(_local, attr):
                    delattr(_local, attr)

    @staticmethod
    def _client_ip(request) -> str | None:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
