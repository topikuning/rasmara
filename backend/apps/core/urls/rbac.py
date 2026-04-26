"""URL: /api/v1/users, /roles, /permissions, /menus, /audit-logs"""
from rest_framework.routers import DefaultRouter

from ..api.rbac_views import (
    AuditLogViewSet,
    MenuViewSet,
    PermissionViewSet,
    RoleViewSet,
    UserViewSet,
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("roles", RoleViewSet, basename="role")
router.register("permissions", PermissionViewSet, basename="permission")
router.register("menus", MenuViewSet, basename="menu")
router.register("audit-logs", AuditLogViewSet, basename="audit-log")

urlpatterns = router.urls
