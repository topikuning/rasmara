"""Model Variation Order, Addendum, Field Observation MC.

Bagian 3.4 + 6 CLAUDE.md.
"""
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models

from common.models import TimeStampedModel


# ====================== Variation Order ======================
class VOStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    UNDER_REVIEW = "UNDER_REVIEW", "Sedang Direview"
    APPROVED = "APPROVED", "Disetujui"
    REJECTED = "REJECTED", "Ditolak"
    BUNDLED = "BUNDLED", "Bundled ke Addendum"


class VOItemAction(models.TextChoices):
    ADD = "ADD", "Tambah Item Baru"
    INCREASE = "INCREASE", "Tambah Volume"
    DECREASE = "DECREASE", "Kurangi Volume"
    MODIFY_SPEC = "MODIFY_SPEC", "Ubah Spesifikasi"
    REMOVE = "REMOVE", "Hapus Item"
    REMOVE_FACILITY = "REMOVE_FACILITY", "Hapus Fasilitas"


class VariationOrder(TimeStampedModel):
    """Usulan perubahan teknis pra-Addendum (Bagian 6.1)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.ForeignKey(
        "contract.Contract", on_delete=models.PROTECT, related_name="variation_orders",
    )
    number = models.CharField(max_length=80, db_index=True,
        help_text="Nomor VO unik per kontrak, mis. VO-001/2026.")
    title = models.CharField(max_length=300)
    justification = models.TextField(blank=True,
        help_text="Justifikasi teknis perubahan.")
    status = models.CharField(
        max_length=20, choices=VOStatus.choices,
        default=VOStatus.DRAFT, db_index=True,
    )

    # Audit aksi state
    submitted_at = models.DateTimeField(null=True, blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="submitted_vos",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="reviewed_vos",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="approved_vos",
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="rejected_vos",
    )
    rejection_reason = models.TextField(blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        db_table = "variation_order"
        ordering = ["contract", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["contract", "number"],
                name="vo_unique_contract_number",
            ),
        ]
        indexes = [
            models.Index(fields=["contract", "status"], name="vo_contract_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.contract.number}/{self.number} ({self.get_status_display()})"


class VOItem(TimeStampedModel):
    """Aksi perubahan dalam VO (Bagian 6.2)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vo = models.ForeignKey(
        VariationOrder, on_delete=models.CASCADE, related_name="items",
    )
    action = models.CharField(
        max_length=20, choices=VOItemAction.choices, db_index=True,
    )

    # Untuk ADD/INCREASE/DECREASE/MODIFY_SPEC/REMOVE: source dari item BOQ existing
    # Untuk ADD: null (item baru)
    source_boq_item = models.ForeignKey(
        "boq.BOQItem", null=True, blank=True,
        on_delete=models.PROTECT, related_name="vo_items",
        help_text="Item BOQ existing yang di-modifikasi/hapus. Null utk ADD.",
    )

    # Untuk ADD: facility tujuan + parent_boq_item utk hirarki + atribut item
    facility = models.ForeignKey(
        "contract.Facility", null=True, blank=True,
        on_delete=models.PROTECT, related_name="vo_items",
        help_text="Fasilitas tujuan (utk ADD / REMOVE_FACILITY).",
    )
    parent_boq_item = models.ForeignKey(
        "boq.BOQItem", null=True, blank=True,
        on_delete=models.PROTECT, related_name="vo_child_items",
        help_text="Parent saat ADD (kosong = root di fasilitas).",
    )

    # Atribut item baru (utk ADD) atau perubahan (utk MODIFY_SPEC/INCREASE/DECREASE)
    code = models.CharField(max_length=40, blank=True)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=30, blank=True)
    new_description = models.TextField(blank=True,
        help_text="Spec baru (utk MODIFY_SPEC).")
    new_unit = models.CharField(max_length=30, blank=True)

    # Untuk INCREASE/DECREASE: volume_delta (signed). + utk increase, - utk decrease.
    # Untuk ADD: pakai field ini sebagai volume awal item baru (positif).
    volume_delta = models.DecimalField(
        max_digits=18, decimal_places=4, default=Decimal("0"),
        help_text="Selisih volume (signed). Atau volume awal utk ADD.",
    )
    unit_price = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0"),
        help_text="Harga satuan PRE-PPN. Utk ADD/MODIFY_SPEC.",
    )

    notes = models.TextField(blank=True)

    class Meta:
        db_table = "vo_item"
        ordering = ["vo", "created_at"]
        indexes = [
            models.Index(fields=["vo", "action"], name="vo_item_vo_action_idx"),
            models.Index(fields=["source_boq_item"], name="vo_item_source_idx"),
            models.Index(fields=["facility"], name="vo_item_facility_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.vo.number} - {self.get_action_display()}"


# ====================== Addendum (rewrite stub) ======================
class AddendumType(models.TextChoices):
    CCO = "CCO", "Contract Change Order (Lingkup)"
    EXTENSION = "EXTENSION", "Perpanjangan Durasi"
    VALUE_CHANGE = "VALUE_CHANGE", "Perubahan Nilai"
    COMBINED = "COMBINED", "Gabungan"


class AddendumStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SIGNED = "SIGNED", "Sudah Tandatangan"


class Addendum(TimeStampedModel):
    """Dokumen legal perubahan kontrak (Bagian 6.3)."""

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

    # Bundle VO via M2M through (membatasi 1 VO max 1 addendum via unique)
    vos = models.ManyToManyField(
        VariationOrder, through="AddendumVO", related_name="addenda",
    )

    # Dampak nilai/durasi (di-set saat sign)
    value_delta = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0"),
        help_text="Selisih nilai (POST-PPN). Bisa positif/negatif.",
    )
    days_delta = models.IntegerField(default=0,
        help_text="Selisih durasi (hari). Diterapkan ke contract.end_date saat sign.")
    new_end_date = models.DateField(null=True, blank=True,
        help_text="Tanggal selesai baru (utk EXTENSION/COMBINED).")

    signed_at = models.DateTimeField(null=True, blank=True)
    signed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="signed_addenda",
    )
    document = models.FileField(upload_to="addenda/%Y/", blank=True, null=True)

    # KPA approval (Inv. 7) — diisi saat |value_delta| > 10% nilai original
    kpa_approval = models.JSONField(null=True, blank=True,
        help_text="JSON: {signed_by, signed_at, document_path, nip}.")

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
        return f"{self.contract.number}/{self.number} ({self.get_status_display()})"


class AddendumVO(models.Model):
    """Through table Addendum-VO. UNIQUE(vo) → 1 VO max 1 addendum."""

    id = models.AutoField(primary_key=True)
    addendum = models.ForeignKey(Addendum, on_delete=models.CASCADE)
    vo = models.ForeignKey(VariationOrder, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "addendum_vo"
        constraints = [
            models.UniqueConstraint(fields=["addendum", "vo"],
                                      name="addvo_unique_pair"),
            models.UniqueConstraint(fields=["vo"],
                                      name="addvo_unique_vo_max1"),
        ]


# ====================== Field Observation (MC) ======================
class MCType(models.TextChoices):
    MC_0 = "MC-0", "MC-0 (Pengukuran Awal)"
    MC_INTERIM = "MC-INTERIM", "MC Interim"


class FieldObservation(TimeStampedModel):
    """Berita Acara Mutual Check (MC) — pengukuran lapangan (Bagian 3.4 + 8.3).

    Bukan dokumen legal, sumber justifikasi VO. MC-0 unik per kontrak (Inv. 8).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.ForeignKey(
        "contract.Contract", on_delete=models.PROTECT, related_name="field_observations",
    )
    type = models.CharField(
        max_length=20, choices=MCType.choices,
        default=MCType.MC_INTERIM, db_index=True,
    )
    location = models.ForeignKey(
        "contract.Location", null=True, blank=True,
        on_delete=models.PROTECT, related_name="field_observations",
    )
    observed_at = models.DateTimeField(
        help_text="Tanggal & waktu pengukuran lapangan.",
    )
    notes = models.TextField(blank=True,
        help_text="Catatan pengukuran, kondisi lapangan, dst.")
    document = models.FileField(upload_to="field_obs/%Y/", blank=True, null=True,
        help_text="Berita Acara MC scan/PDF.")

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="field_observations_submitted",
    )

    class Meta:
        db_table = "field_observation"
        ordering = ["contract", "-observed_at"]
        constraints = [
            # Inv. 8: MC-0 unik per kontrak.
            models.UniqueConstraint(
                fields=["contract"],
                condition=models.Q(type="MC-0"),
                name="mc0_unique_per_contract",
            ),
        ]
        indexes = [
            models.Index(fields=["contract", "type", "-observed_at"],
                          name="mc_contract_type_ts_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.contract.number} - {self.type} @ {self.observed_at:%Y-%m-%d}"


class FieldObservationPhoto(TimeStampedModel):
    """Foto bukti MC."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    observation = models.ForeignKey(
        FieldObservation, on_delete=models.CASCADE, related_name="photos",
    )
    file = models.ImageField(upload_to="field_obs/photos/%Y/%m/")
    thumbnail = models.ImageField(upload_to="field_obs/photos/%Y/%m/thumb/",
                                    null=True, blank=True)
    caption = models.CharField(max_length=300, blank=True)
    taken_at = models.DateTimeField(null=True, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )

    class Meta:
        db_table = "field_observation_photo"
        ordering = ["observation", "-taken_at"]
