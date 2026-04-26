"""Model BOQ: BOQRevision (versioning V0/V1/...) & BOQItem (hirarki 4 level).

Bagian 3.3 + 5 + 7 CLAUDE.md.
"""
import uuid
from decimal import Decimal

from django.db import models

from common.models import TimeStampedModel


# =================== BOQRevision ===================
class BOQRevisionStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    APPROVED = "APPROVED", "Disetujui"
    SUPERSEDED = "SUPERSEDED", "Digantikan"


class ChangeType(models.TextChoices):
    UNCHANGED = "UNCHANGED", "Tidak berubah"
    MODIFIED = "MODIFIED", "Diubah"
    ADDED = "ADDED", "Ditambah"
    REMOVED = "REMOVED", "Dihapus"


class BOQRevision(TimeStampedModel):
    """Revisi BOQ — V0 (baseline kontrak) sampai V1, V2, ... (lahir dari Addendum).

    Invariant Bagian 9:
      #1 Exactly-one active per contract -> partial unique index.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.ForeignKey(
        "contract.Contract", on_delete=models.PROTECT, related_name="boq_revisions",
    )
    version = models.IntegerField(
        help_text="0 = baseline kontrak, 1+ = dari Addendum.",
    )
    status = models.CharField(max_length=20, choices=BOQRevisionStatus.choices,
                                default=BOQRevisionStatus.DRAFT, db_index=True)
    is_active = models.BooleanField(default=False, db_index=True,
        help_text="Hanya 1 revisi aktif per kontrak (Inv. 1).")

    # Nullable: V0 tidak terikat addendum. Diisi saat addendum SIGNED -> spawn revisi baru.
    addendum = models.ForeignKey(
        "change.Addendum", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="spawned_revisions",
    )

    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        "core.User", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="approved_boq_revisions",
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "boq_revision"
        ordering = ["contract", "version"]
        constraints = [
            # Inv. 1: maksimal satu revisi is_active=true per kontrak.
            models.UniqueConstraint(
                fields=["contract"],
                condition=models.Q(is_active=True),
                name="boqrev_unique_active_per_contract",
            ),
            models.UniqueConstraint(
                fields=["contract", "version"],
                name="boqrev_unique_contract_version",
            ),
        ]
        indexes = [
            models.Index(fields=["contract", "is_active"], name="boqrev_contract_active_idx"),
            models.Index(fields=["addendum"], name="boqrev_addendum_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.contract.number} V{self.version} ({self.get_status_display()})"


# =================== BOQItem ===================
class BOQItem(TimeStampedModel):
    """Item BOQ — bisa parent (agregator) atau leaf (hitung progres).

    Hirarki 4 level (0-3) via parent_id self-FK NO CASCADE (Inv. 13).
    full_code = path titik dari root, mis. "4.A.1.a".
    weight_pct = total_price / sum(total_price seluruh leaf di kontrak).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    boq_revision = models.ForeignKey(
        BOQRevision, on_delete=models.CASCADE, related_name="items",
    )
    facility = models.ForeignKey(
        "contract.Facility", on_delete=models.PROTECT, related_name="boq_items",
    )

    code = models.CharField(max_length=40, db_index=True,
        help_text="Kode segmen, mis. '4', 'A', '1', 'a'. Unik per (revisi, fasilitas).")
    full_code = models.CharField(max_length=200, db_index=True, blank=True,
        help_text="Path titik dari root, mis. '4.A.1.a'. Auto-derived.")
    description = models.TextField()
    unit = models.CharField(max_length=30, blank=True)
    volume = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("0"))
    unit_price = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"),
        help_text="PRE-PPN (Bagian 7).")
    total_price = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"),
        help_text="volume * unit_price. Untuk parent: aggregate dari child leaf.")
    weight_pct = models.DecimalField(max_digits=7, decimal_places=4, default=Decimal("0"),
        help_text="% kontribusi di kontrak (otomatis di-recompute).")

    # Hirarki — NO CASCADE (Inv. 13)
    parent = models.ForeignKey(
        "self", null=True, blank=True,
        on_delete=models.DO_NOTHING,  # Inv. 13: clear di app layer dulu
        related_name="children", db_constraint=False,
    )
    level = models.IntegerField(default=0, db_index=True,
        help_text="Kedalaman dari root (0..3).")
    display_order = models.IntegerField(default=0, db_index=True)

    # Leaf flag — di-derive dari graph (item tanpa anak aktif = leaf)
    is_leaf = models.BooleanField(default=True, db_index=True)

    # Source link untuk diff antar revisi (Bagian 5.3)
    source_item = models.ForeignKey(
        "self", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="successors",
        help_text="Pendahulu di revisi sebelumnya. Null = item baru.",
    )
    change_type = models.CharField(
        max_length=20, choices=ChangeType.choices, default=ChangeType.UNCHANGED,
        db_index=True,
    )

    # Snapshot atribut lama untuk audit (saat MODIFIED)
    old_description = models.TextField(blank=True)
    old_unit = models.CharField(max_length=30, blank=True)

    # Planning untuk kurva-S
    planned_start_week = models.IntegerField(null=True, blank=True,
        help_text="Minggu mulai (1-based). Null = tidak terjadwal.")
    planned_duration_weeks = models.IntegerField(null=True, blank=True,
        help_text="Durasi rencana dalam minggu.")

    notes = models.TextField(blank=True)

    class Meta:
        db_table = "boq_item"
        ordering = ["facility", "display_order", "full_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["boq_revision", "facility", "code"],
                name="boqitem_unique_rev_fac_code",
            ),
        ]
        indexes = [
            models.Index(fields=["boq_revision", "is_leaf"], name="boqitem_rev_leaf_idx"),
            models.Index(fields=["boq_revision", "facility"], name="boqitem_rev_fac_idx"),
            models.Index(fields=["parent"], name="boqitem_parent_idx"),
            models.Index(fields=["source_item"], name="boqitem_source_idx"),
            models.Index(fields=["full_code"], name="boqitem_fullcode_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.full_code or self.code} - {self.description[:60]}"

    def compute_full_code(self) -> str:
        """Walk parent chain to build path."""
        parts = [self.code]
        node = self.parent
        seen = set()
        while node and node.id not in seen:
            seen.add(node.id)
            parts.append(node.code)
            node = node.parent
        return ".".join(reversed(parts))
