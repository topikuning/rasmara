"""Signal: auto-create BOQ V0 (DRAFT) saat Contract baru dibuat.

Mengikuti CLAUDE.md Bagian 5.2 — V0 adalah baseline kontrak, dibuat saat kontrak baru.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.contract.models import Contract

from .models import BOQRevision, BOQRevisionStatus


@receiver(post_save, sender=Contract)
def auto_create_v0(sender, instance: Contract, created: bool, **kwargs):
    if not created:
        return
    # Idempotent: cek belum ada V0
    if BOQRevision.objects.filter(contract=instance, version=0).exists():
        return
    BOQRevision.objects.create(
        contract=instance,
        version=0,
        status=BOQRevisionStatus.DRAFT,
        is_active=True,  # V0 langsung aktif (status DRAFT)
        notes="Baseline kontrak (otomatis dibuat saat kontrak dibuat).",
    )
