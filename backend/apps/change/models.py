"""Stub model untuk Modul 5 (VO & Addendum).

Field minimal supaya BOQRevision (Modul 4) bisa membuat FK. Implementasi
penuh state machine, tipe (CCO/EXTENSION/VALUE_CHANGE/COMBINED), KPA approval,
sign flow, bundle VO — akan ditambahkan di Modul 5.
"""
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models

from common.models import TimeStampedModel


class AddendumType(models.TextChoices):
    CCO = "CCO", "Contract Change Order (Lingkup)"
    EXTENSION = "EXTENSION", "Perpanjangan Durasi"
    VALUE_CHANGE = "VALUE_CHANGE", "Perubahan Nilai"
    COMBINED = "COMBINED", "Gabungan"


class AddendumStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SIGNED = "SIGNED", "Sudah Tandatangan"


class Addendum(TimeStampedModel):
    """Addendum kontrak. Implementasi penuh di Modul 5."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.ForeignKey(
        "contract.Contract", on_delete=models.PROTECT, related_name="addenda",
    )
    number = models.CharField(max_length=80,
        help_text="Nomor addendum, mis. 001/ADD/IV/2026.")
    addendum_type = models.CharField(
        max_length=20, choices=AddendumType.choices,
        default=AddendumType.CCO, db_index=True,
    )
    reason = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=AddendumStatus.choices,
        default=AddendumStatus.DRAFT, db_index=True,
    )

    # Dampak nilai/durasi (akan diisi saat sign di Modul 5)
    value_delta = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0"),
        help_text="Selisih nilai (POST-PPN). Bisa positif/negatif.",
    )
    days_delta = models.IntegerField(default=0,
        help_text="Selisih durasi (hari).")

    signed_at = models.DateTimeField(null=True, blank=True)
    signed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="signed_addenda",
    )
    document = models.FileField(upload_to="addenda/%Y/", blank=True, null=True)

    # KPA approval (Inv. 7) — diisi saat |value_delta| > 10% nilai original
    kpa_approval = models.JSONField(null=True, blank=True,
        help_text="JSON: {signed_by, signed_at, document_path}.")

    notes = models.TextField(blank=True)

    class Meta:
        db_table = "addendum"
        ordering = ["contract", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["contract", "number"],
                name="addendum_unique_contract_number",
            ),
        ]
        indexes = [
            models.Index(fields=["contract", "status"], name="addendum_contract_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.contract.number} / {self.number} ({self.get_status_display()})"
