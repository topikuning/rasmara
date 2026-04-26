"""Model Kontrak, Lokasi, Fasilitas (Bagian 3.2 CLAUDE.md)."""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from common.models import SoftDeleteModel


class ContractStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Aktif"
    ON_HOLD = "ON_HOLD", "Pause"
    COMPLETED = "COMPLETED", "Selesai"
    TERMINATED = "TERMINATED", "Dihentikan"


class Contract(SoftDeleteModel):
    """Kontrak (Bagian 3.2 + 4 + 7 CLAUDE.md).

    Nilai kontrak (original_value, current_value) disimpan POST-PPN.
    BOQ items disimpan PRE-PPN. PPN per kontrak (default 11%).
    """

    number = models.CharField(max_length=80, unique=True, db_index=True,
                               help_text="Nomor kontrak unik, mis. 001/KONTRAK/IV/2026.")
    name = models.CharField(max_length=300)
    ppk = models.ForeignKey(
        "master.PPK", on_delete=models.PROTECT, related_name="contracts",
        help_text="PPK pemilik kontrak.",
    )
    contractor = models.ForeignKey(
        "master.Company", on_delete=models.PROTECT, related_name="contracts_as_contractor",
        help_text="Perusahaan kontraktor pelaksana.",
    )

    fiscal_year = models.IntegerField(
        validators=[MinValueValidator(2000), MaxValueValidator(2100)],
        help_text="Tahun anggaran (mis. 2026).",
    )

    # Nilai POST-PPN (Bagian 7)
    original_value = models.DecimalField(
        max_digits=18, decimal_places=2,
        help_text="Nilai kontrak awal (POST-PPN). Tidak berubah meskipun ada addendum.",
    )
    current_value = models.DecimalField(
        max_digits=18, decimal_places=2,
        help_text="Nilai kontrak saat ini (POST-PPN). Berubah setiap addendum VALUE_CHANGE/COMBINED.",
    )
    ppn_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("11.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        help_text="Persentase PPN. Default 11%.",
    )

    start_date = models.DateField()
    end_date = models.DateField()
    duration_days = models.IntegerField(
        default=0,
        help_text="Durasi total dalam hari (otomatis dihitung di save()).",
    )

    status = models.CharField(
        max_length=20, choices=ContractStatus.choices,
        default=ContractStatus.DRAFT, db_index=True,
    )

    # Godmode (Inv. 14)
    unlock_until = models.DateTimeField(null=True, blank=True,
        help_text="Bila > now(), validasi state-machine di-bypass + audit ditandai.")
    unlock_reason = models.TextField(blank=True)

    document = models.FileField(upload_to="contracts/%Y/", blank=True, null=True,
        help_text="Dokumen PDF kontrak.")
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "contract"
        ordering = ["-fiscal_year", "number"]
        indexes = [
            models.Index(fields=["status", "deleted_at"], name="contract_status_active_idx"),
            models.Index(fields=["fiscal_year", "deleted_at"], name="contract_year_active_idx"),
            models.Index(fields=["ppk", "deleted_at"], name="contract_ppk_active_idx"),
            models.Index(fields=["contractor", "deleted_at"], name="contract_kontr_active_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.number} - {self.name}"

    def save(self, *args, **kwargs):
        # Auto-hitung duration_days dari start/end (inklusif).
        # Bekerja konsisten di semua path: DRF, admin, script, test.
        if self.start_date and self.end_date:
            self.duration_days = (self.end_date - self.start_date).days + 1
        return super().save(*args, **kwargs)

    # ----- helpers nilai (Bagian 7) -----
    @property
    def boq_pre_ppn_value(self) -> Decimal:
        """Sum nilai item BOQ leaf (PRE-PPN) di revisi aktif."""
        try:
            from apps.boq.models import BOQItem
            from django.db.models import Sum
            agg = BOQItem.objects.filter(
                boq_revision__contract=self,
                boq_revision__is_active=True,
                is_leaf=True,
            ).aggregate(total=Sum("total_price"))
            return (agg["total"] or Decimal("0.00")).quantize(Decimal("0.01"))
        except (ImportError, LookupError):
            return Decimal("0.00")

    @property
    def ppn_amount(self) -> Decimal:
        """Nilai PPN dari BOQ pre-PPN."""
        return (self.boq_pre_ppn_value * self.ppn_pct / Decimal("100")).quantize(Decimal("0.01"))

    @property
    def is_godmode_active(self) -> bool:
        from django.utils import timezone
        return bool(self.unlock_until and self.unlock_until > timezone.now())


class Location(SoftDeleteModel):
    """Lokasi proyek di bawah kontrak (Bagian 3.2)."""

    contract = models.ForeignKey(
        Contract, on_delete=models.PROTECT, related_name="locations",
    )
    code = models.CharField(max_length=40, db_index=True,
                            help_text="Kode lokasi unik dalam kontrak.")
    name_desa = models.CharField(max_length=120, blank=True)
    name_kecamatan = models.CharField(max_length=120, blank=True)
    name_kota = models.CharField(max_length=120, blank=True)
    name_provinsi = models.CharField(max_length=120, blank=True)
    full_address = models.TextField(blank=True,
        help_text="Alamat lengkap untuk surat-menyurat.")

    # Koordinat (wajib utk gate aktivasi - Bagian 4)
    latitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True,
        validators=[MinValueValidator(Decimal("-90")), MaxValueValidator(Decimal("90"))],
    )
    longitude = models.DecimalField(
        max_digits=11, decimal_places=7, null=True, blank=True,
        validators=[MinValueValidator(Decimal("-180")), MaxValueValidator(Decimal("180"))],
    )

    # Konsultan MK pengawas (Inv. 16: scope per-lokasi, bukan per-kontrak)
    konsultan = models.ForeignKey(
        "master.Company", on_delete=models.PROTECT, related_name="supervised_locations",
        null=True, blank=True,
        help_text="Konsultan MK pengawas lokasi ini. Inv. 16: filter laporan per-lokasi.",
    )

    notes = models.TextField(blank=True)

    class Meta:
        db_table = "location"
        ordering = ["contract", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["contract", "code"],
                condition=models.Q(deleted_at__isnull=True),
                name="location_unique_contract_code",
            ),
        ]
        indexes = [
            models.Index(fields=["contract", "deleted_at"], name="location_contract_active_idx"),
            models.Index(fields=["konsultan", "deleted_at"], name="location_konsul_active_idx"),
        ]

    def __str__(self) -> str:
        bits = [self.code, self.name_desa, self.name_kecamatan]
        return " - ".join(b for b in bits if b)

    @property
    def has_coordinates(self) -> bool:
        return self.latitude is not None and self.longitude is not None


class Facility(SoftDeleteModel):
    """Fasilitas/bangunan di dalam lokasi (Bagian 3.2)."""

    location = models.ForeignKey(
        Location, on_delete=models.PROTECT, related_name="facilities",
    )
    code = models.CharField(max_length=40, db_index=True,
        help_text="Kode unik per lokasi.")
    master_facility = models.ForeignKey(
        "master.MasterFacility", on_delete=models.PROTECT, related_name="facilities",
        help_text="Tipe fasilitas dari katalog master.",
    )
    name = models.CharField(max_length=200,
        help_text="Nama spesifik fasilitas, mis. 'Gudang Beku 1'.")
    display_order = models.IntegerField(default=0, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "facility"
        ordering = ["location", "display_order", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["location", "code"],
                condition=models.Q(deleted_at__isnull=True),
                name="facility_unique_location_code",
            ),
        ]
        indexes = [
            models.Index(fields=["location", "deleted_at"], name="facility_location_act_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"

    @property
    def contract_id(self):
        return self.location.contract_id
