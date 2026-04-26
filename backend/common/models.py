"""Model dasar yang dipakai semua entitas."""
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """Auto created_at, updated_at."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """PK UUIDv4."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class AuditedModel(UUIDModel, TimeStampedModel):
    """UUID + timestamps + created_by/updated_by."""

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="+",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="+",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        return self.filter(deleted_at__isnull=False)

    def soft_delete(self, user=None):
        return self.update(deleted_at=timezone.now())


# Manager class yang auto-proxy method dari SoftDeleteQuerySet, sehingga
# `Model.objects.alive()` DAN `parent.related_set.alive()` keduanya bekerja.
_SoftDeleteManagerBase = models.Manager.from_queryset(SoftDeleteQuerySet)


class SoftDeleteManager(_SoftDeleteManagerBase):
    """Default manager filter deleted_at IS NULL (Inv. 12).

    Menggunakan from_queryset(SoftDeleteQuerySet) sehingga method alive/dead
    otomatis tersedia di RelatedManager (mis. `contract.locations.alive()`).
    """

    use_in_migrations = True

    def __init__(self, include_deleted: bool = False) -> None:
        super().__init__()
        self._include_deleted = include_deleted

    def get_queryset(self) -> SoftDeleteQuerySet:
        qs = super().get_queryset()
        if not self._include_deleted:
            qs = qs.filter(deleted_at__isnull=True)
        return qs


class SoftDeleteModel(AuditedModel):
    """Soft-delete: set deleted_at, jangan hard-delete."""

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteManager()
    all_objects = SoftDeleteManager(include_deleted=True)

    class Meta:
        abstract = True

    def soft_delete(self, user=None) -> None:
        self.deleted_at = timezone.now()
        if user is not None:
            self.updated_by = user
        self.save(update_fields=["deleted_at", "updated_at", "updated_by"])

    def restore(self) -> None:
        self.deleted_at = None
        self.save(update_fields=["deleted_at", "updated_at"])
