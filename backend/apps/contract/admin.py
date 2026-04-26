from django.contrib import admin

from .models import Contract, Facility, Location


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ("number", "name", "status", "fiscal_year", "ppk", "contractor",
                     "original_value", "current_value", "deleted_at")
    list_filter = ("status", "fiscal_year")
    search_fields = ("number", "name")
    readonly_fields = ("duration_days",)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("contract", "code", "name_kota", "name_provinsi",
                     "latitude", "longitude", "konsultan", "deleted_at")
    list_filter = ("name_provinsi",)
    search_fields = ("code", "name_desa", "name_kecamatan", "name_kota")


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ("location", "code", "name", "master_facility", "display_order", "deleted_at")
    search_fields = ("code", "name")
