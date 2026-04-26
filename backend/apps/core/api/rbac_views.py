"""View RBAC: users, roles, permissions, menus, audit-logs."""
from django.contrib.auth import get_user_model
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import AuditLog, Menu, Permission, Role
from ..permissions import HasPermissionCode, IsSuperuser
from .serializers import (
    AuditLogSerializer,
    MenuSerializer,
    PermissionSerializer,
    RoleMenusUpdateSerializer,
    RolePermissionsUpdateSerializer,
    RoleSerializer,
    UserCreateSerializer,
    UserSerializer,
)

User = get_user_model()


# ---------- Permission ----------
class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/v1/permissions/  (katalog seluruh permission code).

    Tidak ada endpoint create/update/delete — permission ditambah via seed/migration.
    """

    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = (IsAuthenticated, HasPermissionCode)
    required_permission = "role.read"
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    search_fields = ["code", "name", "module", "action"]
    filterset_fields = ["module"]
    pagination_class = None  # ringan, kirim semua


# ---------- Role ----------
class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all().order_by("name")
    serializer_class = RoleSerializer
    permission_classes = (IsAuthenticated, HasPermissionCode)
    required_permission = "role.read"
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    search_fields = ["code", "name", "description"]

    def get_required_permission(self) -> str:
        return {
            "list": "role.read", "retrieve": "role.read",
            "create": "role.create", "update": "role.update",
            "partial_update": "role.update", "destroy": "role.delete",
        }.get(self.action, "role.read")

    def initial(self, request, *args, **kwargs):
        # set required_permission per action
        super().initial(request, *args, **kwargs)
        self.required_permission = self.get_required_permission()

    def perform_destroy(self, instance: Role) -> None:
        if instance.is_system:
            from common.exceptions import DomainError
            raise DomainError("Role bawaan tidak boleh dihapus.", code="SYSTEM_ROLE")
        super().perform_destroy(instance)

    @action(detail=True, methods=["put"], url_path="permissions")
    @transaction.atomic
    def set_permissions(self, request, pk=None):
        role = self.get_object()
        if not request.user.has_perm_code("role.update"):
            return Response({"error": {"code": "PERMISSION_DENIED",
                                        "message": "Membutuhkan role.update"}}, status=403)
        s = RolePermissionsUpdateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        codes = s.validated_data["permission_codes"]
        perms = list(Permission.objects.filter(code__in=codes))
        role.permissions.set(perms)
        return Response(RoleSerializer(role).data)

    @action(detail=True, methods=["put"], url_path="menus")
    @transaction.atomic
    def set_menus(self, request, pk=None):
        role = self.get_object()
        if not request.user.has_perm_code("role.update"):
            return Response({"error": {"code": "PERMISSION_DENIED",
                                        "message": "Membutuhkan role.update"}}, status=403)
        s = RoleMenusUpdateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        codes = s.validated_data["menu_codes"]
        menus = list(Menu.objects.filter(code__in=codes))
        role.menus.set(menus)
        return Response(RoleSerializer(role).data)


# ---------- Menu ----------
class MenuViewSet(viewsets.ModelViewSet):
    queryset = Menu.objects.all().order_by("order", "label")
    serializer_class = MenuSerializer
    permission_classes = (IsAuthenticated, HasPermissionCode)
    required_permission = "menu.read"
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    search_fields = ["code", "label", "route"]
    filterset_fields = ["parent", "is_active"]

    def get_required_permission(self) -> str:
        return {
            "list": "menu.read", "retrieve": "menu.read",
            "create": "menu.create", "update": "menu.update",
            "partial_update": "menu.update", "destroy": "menu.delete",
        }.get(self.action, "menu.read")

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.required_permission = self.get_required_permission()


# ---------- User ----------
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related("role").order_by("username")
    permission_classes = (IsAuthenticated, HasPermissionCode)
    required_permission = "user.read"
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    search_fields = ["username", "email", "full_name", "phone"]
    filterset_fields = ["role", "is_active"]

    def get_required_permission(self) -> str:
        return {
            "list": "user.read", "retrieve": "user.read",
            "create": "user.create", "update": "user.update",
            "partial_update": "user.update", "destroy": "user.delete",
            "reset_password": "user.update",
        }.get(self.action, "user.read")

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.required_permission = self.get_required_permission()

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def create(self, request, *args, **kwargs):
        s = UserCreateSerializer(data=request.data, context={"request": request})
        s.is_valid(raise_exception=True)
        user = s.save()
        out = UserSerializer(user).data
        # one-time field initial password
        if hasattr(user, "_initial_password"):
            out["initial_password"] = user._initial_password
        return Response(out, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="reset-password")
    def reset_password(self, request, pk=None):
        user = self.get_object()
        new_pwd = User.objects.make_random_password(length=10)
        user.set_password(new_pwd)
        user.must_change_password = True
        user.save(update_fields=["password", "must_change_password", "updated_at"])
        return Response({"initial_password": new_pwd,
                         "detail": "Password baru sudah di-set. User wajib ganti saat login berikutnya."})


# ---------- Audit ----------
class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("user").order_by("-ts")
    serializer_class = AuditLogSerializer
    permission_classes = (IsAuthenticated, HasPermissionCode)
    required_permission = "audit.read"
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    search_fields = ["entity_type", "entity_repr", "action"]
    filterset_fields = ["action", "entity_type", "user", "godmode_bypass"]
    ordering_fields = ["ts"]
