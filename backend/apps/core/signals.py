"""Signal: tulis audit log saat model berubah.

Strategi: diff field konkret yang relevan, hindari noise (auto-now, password hash).
"""
from typing import Any

from django.contrib.auth.signals import user_logged_in, user_login_failed, user_logged_out
from django.db import models
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .middleware import get_audit_context
from .models import AuditAction, AuditLog, Permission, Role, RolePermission, RoleMenu, Menu, User

# Field yang TIDAK perlu masuk diff
IGNORE_FIELDS = {"password", "last_login", "updated_at", "created_at", "id"}

# Model yang DI-AUDIT (class object). Tambahkan di sini saat modul baru di-deploy.
AUDITED_MODELS: set[type[models.Model]] = {
    User,
    Role,
    Permission,
    Menu,
    RolePermission,
    RoleMenu,
}


def _serialize(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _snapshot(instance: models.Model) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for field in instance._meta.concrete_fields:
        if field.name in IGNORE_FIELDS:
            continue
        if isinstance(field, (models.ManyToManyField,)):
            continue
        try:
            out[field.name] = _serialize(getattr(instance, field.name))
        except Exception:  # noqa: BLE001
            pass
    return out


def _diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for k, av in after.items():
        bv = before.get(k)
        if bv != av:
            out[k] = {"before": bv, "after": av}
    return out


@receiver(pre_save)
def _capture_pre_save(sender, instance, **kwargs):
    if sender not in AUDITED_MODELS:
        return
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance.__rasmara_audit_before = _snapshot(old)
        except sender.DoesNotExist:
            instance.__rasmara_audit_before = {}
    else:
        instance.__rasmara_audit_before = None


@receiver(post_save)
def _capture_post_save(sender, instance, created, **kwargs):
    if sender not in AUDITED_MODELS:
        return
    ctx = get_audit_context()
    after = _snapshot(instance)
    before = getattr(instance, "__rasmara_audit_before", None)

    if created:
        action = AuditAction.CREATE
        changes = {k: {"before": None, "after": v} for k, v in after.items()}
    else:
        action = AuditAction.UPDATE
        changes = _diff(before or {}, after)
        if not changes:
            return  # tidak ada perubahan substantif

    AuditLog.objects.create(
        user=ctx["user"],
        action=action,
        entity_type=sender.__name__,
        entity_id=getattr(instance, "id", None),
        entity_repr=str(instance)[:255],
        changes=changes,
        ip_address=ctx["ip_address"],
        user_agent=ctx["user_agent"],
        godmode_bypass=ctx["godmode_bypass"],
        unlock_reason=ctx["unlock_reason"],
    )


@receiver(post_delete)
def _capture_post_delete(sender, instance, **kwargs):
    if sender not in AUDITED_MODELS:
        return
    ctx = get_audit_context()
    AuditLog.objects.create(
        user=ctx["user"],
        action=AuditAction.DELETE,
        entity_type=sender.__name__,
        entity_id=getattr(instance, "id", None),
        entity_repr=str(instance)[:255],
        changes={},
        ip_address=ctx["ip_address"],
        user_agent=ctx["user_agent"],
    )


# ---------- Auth events ----------
@receiver(user_logged_in)
def _on_login(sender, request, user, **kwargs):
    ctx = get_audit_context()
    AuditLog.objects.create(
        user=user, action=AuditAction.LOGIN, entity_type="User",
        entity_id=user.id, entity_repr=str(user)[:255],
        ip_address=ctx["ip_address"], user_agent=ctx["user_agent"],
    )


@receiver(user_logged_out)
def _on_logout(sender, request, user, **kwargs):
    if user is None:
        return
    ctx = get_audit_context()
    AuditLog.objects.create(
        user=user, action=AuditAction.LOGOUT, entity_type="User",
        entity_id=user.id, entity_repr=str(user)[:255],
        ip_address=ctx["ip_address"], user_agent=ctx["user_agent"],
    )


@receiver(user_login_failed)
def _on_login_failed(sender, credentials, request, **kwargs):
    ctx = get_audit_context()
    AuditLog.objects.create(
        user=None, action=AuditAction.LOGIN_FAILED, entity_type="User",
        entity_repr=credentials.get("username", "?")[:255],
        ip_address=ctx["ip_address"], user_agent=ctx["user_agent"],
    )
