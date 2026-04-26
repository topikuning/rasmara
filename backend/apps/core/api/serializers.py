"""Serializer untuk auth & RBAC."""
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from common.security import generate_password

from ..models import AuditLog, Menu, Permission, Role, User


# ---------- Permission ----------
class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "code", "name", "module", "action", "description"]
        read_only_fields = ["id"]


# ---------- Role ----------
class RoleSerializer(serializers.ModelSerializer):
    permission_codes = serializers.SerializerMethodField()
    menu_codes = serializers.SerializerMethodField()
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            "id", "code", "name", "description", "is_system",
            "permission_codes", "menu_codes", "user_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "is_system", "created_at", "updated_at"]

    def get_permission_codes(self, obj: Role) -> list[str]:
        return list(obj.permissions.values_list("code", flat=True))

    def get_menu_codes(self, obj: Role) -> list[str]:
        return list(obj.menus.values_list("code", flat=True))

    def get_user_count(self, obj: Role) -> int:
        return obj.users.count()


class RolePermissionsUpdateSerializer(serializers.Serializer):
    permission_codes = serializers.ListField(child=serializers.CharField(), allow_empty=True)


class RoleMenusUpdateSerializer(serializers.Serializer):
    menu_codes = serializers.ListField(child=serializers.CharField(), allow_empty=True)


# ---------- Menu ----------
class MenuSerializer(serializers.ModelSerializer):
    parent_code = serializers.CharField(source="parent.code", read_only=True, allow_null=True)
    children = serializers.SerializerMethodField()

    class Meta:
        model = Menu
        fields = [
            "id", "code", "label", "icon", "route", "order",
            "parent", "parent_code", "is_active", "children",
        ]
        read_only_fields = ["id"]

    def get_children(self, obj: Menu) -> list[dict]:
        kids = obj.children.filter(is_active=True).order_by("order", "label")
        return MenuSerializer(kids, many=True, context=self.context).data


# ---------- User ----------
class UserSerializer(serializers.ModelSerializer):
    role_code = serializers.CharField(source="role.code", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), source="role", required=False, allow_null=True
    )

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "full_name", "phone",
            "role_id", "role_code", "role_name",
            "assigned_contract_ids",
            "must_change_password", "auto_provisioned",
            "is_active", "is_staff", "is_superuser",
            "last_login", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "role_code", "role_name",
            "auto_provisioned", "last_login", "created_at", "updated_at",
        ]


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), source="role", required=False, allow_null=True
    )

    class Meta:
        model = User
        fields = [
            "username", "email", "full_name", "phone",
            "role_id", "assigned_contract_ids",
            "is_active", "password",
        ]

    def create(self, validated_data: dict):
        password = validated_data.pop("password", None) or generate_password()
        user = User(**validated_data, must_change_password=True)
        user.set_password(password)
        user.save()
        user._initial_password = password  # untuk dilihat admin sekali
        return user


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=False, allow_blank=True)
    new_password = serializers.CharField()

    def validate_new_password(self, v: str) -> str:
        validate_password(v)
        return v


# ---------- Auth ----------
class LoginSerializer(TokenObtainPairSerializer):
    """JWT login + tambahan info user."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["role_code"] = user.role.code if user.role_id else None
        return token

    def validate(self, attrs: dict) -> dict:
        data = super().validate(attrs)
        user = self.user
        data["must_change_password"] = user.must_change_password
        data["user"] = MeSerializer(user, context=self.context).data
        return data


class MeSerializer(serializers.ModelSerializer):
    role_code = serializers.CharField(source="role.code", read_only=True, default=None)
    role_name = serializers.CharField(source="role.name", read_only=True, default=None)
    permission_codes = serializers.SerializerMethodField()
    menu_tree = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "full_name", "phone",
            "role_code", "role_name",
            "assigned_contract_ids",
            "must_change_password", "is_superuser", "is_active",
            "permission_codes", "menu_tree",
        ]

    def get_permission_codes(self, user: User) -> list[str]:
        if user.is_superuser:
            return list(Permission.objects.values_list("code", flat=True))
        if user.role_id is None:
            return []
        return list(user.role.permissions.values_list("code", flat=True))

    def get_menu_tree(self, user: User) -> list[dict]:
        if user.is_superuser:
            roots = Menu.objects.filter(parent__isnull=True, is_active=True).order_by("order", "label")
        elif user.role_id is None:
            return []
        else:
            roots = user.role.menus.filter(parent__isnull=True, is_active=True).order_by("order", "label")
        return MenuSerializer(roots, many=True, context=self.context).data


# ---------- Audit ----------
class AuditLogSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True, default=None)
    user_full_name = serializers.CharField(source="user.full_name", read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = [
            "id", "user", "user_username", "user_full_name",
            "action", "entity_type", "entity_id", "entity_repr",
            "changes", "ip_address", "user_agent",
            "godmode_bypass", "unlock_reason", "extra", "ts",
        ]
        read_only_fields = fields
