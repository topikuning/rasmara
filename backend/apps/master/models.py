"""Model master data: Company, PPK, MasterFacility, MasterWorkCode."""
from django.conf import settings
from django.db import models

from common.models import SoftDeleteModel


class CompanyType(models.TextChoices):
    KONTRAKTOR = "KONTRAKTOR", "Kontraktor"
    KONSULTAN = "KONSULTAN", "Konsultan MK"
    SUPPLIER = "SUPPLIER", "Supplier"
    OTHER = "OTHER", "Lainnya"


class Company(SoftDeleteModel):
    code = models.CharField(max_length=40, unique=True, db_index=True,
                            help_text="Kode unik perusahaan, mis. PT-ABC.")
    name = models.CharField(max_length=200)
    npwp = models.CharField(max_length=20, blank=True,
                             help_text="Format: 12.345.678.9-012.345 atau 16-digit baru.")
    type = models.CharField(max_length=20, choices=CompanyType.choices,
                             default=CompanyType.KONTRAKTOR, db_index=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    pic_name = models.CharField(max_length=160, blank=True,
                                 help_text="Nama person-in-charge.")
    pic_phone = models.CharField(max_length=30, blank=True)

    # Auto-provisioned user (Inv. 15)
    default_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="default_for_companies",
        help_text="User default yang dibuat otomatis saat company dibuat.",
    )

    class Meta:
        db_table = "company"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["type", "deleted_at"], name="company_type_active_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class PPK(SoftDeleteModel):
    """Pejabat Pembuat Komitmen."""

    nip = models.CharField(max_length=30, unique=True, db_index=True,
                            help_text="Nomor Induk Pegawai (18 digit umumnya).")
    full_name = models.CharField(max_length=160)
    jabatan = models.CharField(max_length=160, blank=True,
                                help_text="Mis. PPK Direktorat XYZ.")
    satker = models.CharField(max_length=160, blank=True,
                                help_text="Satuan kerja induk.")
    whatsapp = models.CharField(max_length=30, blank=True,
                                 help_text="Format internasional, mis. 6281234567890. Untuk notifikasi WA.")
    email = models.EmailField(blank=True)

    # Terikat ke User (Bagian 3.1)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="ppk_profile",
    )

    class Meta:
        db_table = "ppk"
        ordering = ["full_name"]
        verbose_name = "PPK"
        verbose_name_plural = "PPK"

    def __str__(self) -> str:
        return f"{self.full_name} (NIP {self.nip})"


class MasterFacility(SoftDeleteModel):
    """Katalog tipe fasilitas standar (Gudang Beku, Pabrik Es, dst.)."""

    code = models.CharField(max_length=40, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "master_facility"
        ordering = ["name"]
        verbose_name = "Master Fasilitas"
        verbose_name_plural = "Master Fasilitas"

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class MasterWorkCode(SoftDeleteModel):
    """Katalog kode pekerjaan standar dengan kategori."""

    class Category(models.TextChoices):
        PERSIAPAN = "PERSIAPAN", "Persiapan"
        STRUKTURAL = "STRUKTURAL", "Struktural"
        ARSITEKTURAL = "ARSITEKTURAL", "Arsitektural"
        MEP = "MEP", "Mekanikal/Elektrikal/Plumbing"
        FINISHING = "FINISHING", "Finishing"
        FURNITURE = "FURNITURE", "Furniture & Equipment"
        LANSEKAP = "LANSEKAP", "Lansekap & Sitework"
        LAINNYA = "LAINNYA", "Lainnya"

    code = models.CharField(max_length=40, unique=True, db_index=True,
                             help_text="Kode pekerjaan, mis. STR-001.")
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=Category.choices,
                                 default=Category.LAINNYA, db_index=True)
    default_unit = models.CharField(max_length=20, blank=True,
                                     help_text="Satuan default, mis. m2, m3, ls, unit, kg.")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "master_work_code"
        ordering = ["category", "code"]
        verbose_name = "Master Kode Pekerjaan"
        verbose_name_plural = "Master Kode Pekerjaan"

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"
