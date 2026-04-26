"""Model core: User, Role, Permission, Menu, AuditLog."""
import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from common.models import TimeStampedModel


# ---------- Permission catalog ----------
class Permission(TimeStampedModel):
    """Permission domain (module.action), DINAMIS di DB.

    Berbeda dari django.contrib.auth.models.Permission — kita pakai sendiri
    supaya bisa diedit superadmin tanpa migration.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=80, unique=True, db_index=True,
                            help_text="Format: module.action, mis. contract.update")
    name = models.CharField(max_length=120)
    module = models.CharField(max_length=40, db_index=True)
    action = models.CharField(max_length=40)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "permission"
        ordering = ["module", "action"]

    def __str__(self) -> str:
        return self.code


# ---------- Role ----------
class Role(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=40, unique=True, db_index=True,
                            help_text="superadmin, admin_pusat, ppk, manager, konsultan, kontraktor, itjen, viewer")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False,
                                     help_text="Role bawaan tidak boleh dihapus.")
    permissions = models.ManyToManyField(Permission, through="RolePermission", related_name="roles")
    menus = models.ManyToManyField("Menu", through="RoleMenu", related_name="roles")

    class Meta:
        db_table = "role"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "role_permission"
        unique_together = [("role", "permission")]


# ---------- Menu ----------
class Menu(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=60, unique=True, db_index=True)
    label = models.CharField(max_length=120)
    icon = models.CharField(max_length=40, blank=True, help_text="Nama ikon lucide")
    route = models.CharField(max_length=200, blank=True)
    order = models.IntegerField(default=0, db_index=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="children")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "menu"
        ordering = ["order", "label"]

    def __str__(self) -> str:
        return self.label


class RoleMenu(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "role_menu"
        unique_together = [("role", "menu")]


# ---------- User ----------
class UserManager(BaseUserManager):
    def create_user(self, username: str, password: str | None = None, **extra) -> "User":
        if not username:
            raise ValueError("Username wajib diisi")
        user = self.model(username=username, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, username: str, password: str | None = None, **extra) -> "User":
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("must_change_password", False)
        return self.create_user(username, password, **extra)


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """Custom user model RASMARA."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=80, unique=True, db_index=True)
    email = models.EmailField(blank=True)
    full_name = models.CharField(max_length=160)
    phone = models.CharField(max_length=30, blank=True,
                              help_text="Format internasional, mis. 6281234567890")
    role = models.ForeignKey(Role, null=True, blank=True, on_delete=models.SET_NULL,
                              related_name="users")

    # Scope: null = lihat semua kontrak; list of UUID = scoped (Bagian 2)
    assigned_contract_ids = models.JSONField(null=True, blank=True, default=None,
        help_text="Null = lihat semua. List = hanya kontrak ini.")

    # Flags
    must_change_password = models.BooleanField(default=False)
    auto_provisioned = models.BooleanField(default=False,
        help_text="True jika user di-spawn otomatis saat create Company/PPK.")

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # FK opsional balik ke Company / PPK akan ditambahkan saat modul Master Data
    # via add_to_class atau sebagai nullable di sana. Hindari import circular.

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    class Meta:
        db_table = "user"
        ordering = ["username"]

    def __str__(self) -> str:
        return f"{self.username} ({self.full_name})"

    # ----- Permission helpers -----
    def has_perm_code(self, code: str) -> bool:
        """Cek permission via code (mis. 'contract.update')."""
        if self.is_superuser:
            return True
        if self.role_id is None:
            return False
        return RolePermission.objects.filter(role_id=self.role_id, permission__code=code).exists()

    def can_access_contract(self, contract_id) -> bool:
        """Scope contract: None=all, list=match."""
        if self.is_superuser:
            return True
        if self.assigned_contract_ids is None:
            return True
        return str(contract_id) in {str(x) for x in self.assigned_contract_ids}


# ---------- Audit Log ----------
class AuditAction(models.TextChoices):
    CREATE = "CREATE", "Create"
    UPDATE = "UPDATE", "Update"
    DELETE = "DELETE", "Delete"
    LOGIN = "LOGIN", "Login"
    LOGOUT = "LOGOUT", "Logout"
    LOGIN_FAILED = "LOGIN_FAILED", "Login Failed"
    APPROVE = "APPROVE", "Approve"
    REJECT = "REJECT", "Reject"
    SIGN = "SIGN", "Sign"
    SUBMIT = "SUBMIT", "Submit"
    LOCK = "LOCK", "Lock"
    UNLOCK = "UNLOCK", "Unlock"
    GODMODE_BYPASS = "GODMODE_BYPASS", "Godmode Bypass"
    EXPORT = "EXPORT", "Export"
    IMPORT = "IMPORT", "Import"


class AuditLog(models.Model):
    """Catat semua perubahan CRUD + aksi penting (Bagian 12.3)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                              related_name="audit_entries")
    action = models.CharField(max_length=20, choices=AuditAction.choices, db_index=True)
    entity_type = models.CharField(max_length=80, db_index=True)
    entity_id = models.UUIDField(null=True, blank=True, db_index=True)
    entity_repr = models.CharField(max_length=255, blank=True,
        help_text="Snapshot string repr entitas saat audit.")
    changes = models.JSONField(default=dict, blank=True,
        help_text="Diff: {field: {before, after}}")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    godmode_bypass = models.BooleanField(default=False, db_index=True)
    unlock_reason = models.TextField(blank=True)
    extra = models.JSONField(default=dict, blank=True)
    ts = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "audit_log"
        ordering = ["-ts"]
        indexes = [
            models.Index(fields=["entity_type", "entity_id", "-ts"], name="audit_entity_ts_idx"),
            models.Index(fields=["user", "-ts"], name="audit_user_ts_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.action} {self.entity_type} by {self.user_id} @ {self.ts:%Y-%m-%d %H:%M}"
