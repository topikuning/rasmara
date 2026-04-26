"""DRF permission classes berbasis permission code dinamis."""
from rest_framework import permissions


class HasPermissionCode(permissions.BasePermission):
    """Cek user.has_perm_code(code).

    Cara pakai di view:
        permission_classes = (IsAuthenticated, HasPermissionCode)
        required_permission = "contract.update"

    Atau via factory required_perm("contract.update").
    """

    message = "Anda tidak memiliki izin untuk operasi ini."

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        code = getattr(view, "required_permission", None)
        if not code:
            return True
        return request.user.has_perm_code(code)


def required_perm(code: str):
    """Factory: kembalikan kelas permission yang require code spesifik."""

    class _Required(HasPermissionCode):
        message = f"Membutuhkan izin: {code}"

        def has_permission(self, request, view):
            if not request.user or not request.user.is_authenticated:
                return False
            return request.user.has_perm_code(code)

    _Required.__name__ = f"Require_{code.replace('.', '_')}"
    return _Required


class IsSuperuser(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)
