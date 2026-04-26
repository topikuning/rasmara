from django.contrib import admin

from .models import Company, MasterFacility, MasterWorkCode, PPK


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "type", "npwp", "default_user", "deleted_at")
    list_filter = ("type",)
    search_fields = ("code", "name", "npwp", "pic_name", "email")


@admin.register(PPK)
class PPKAdmin(admin.ModelAdmin):
    list_display = ("nip", "full_name", "jabatan", "satker", "user", "deleted_at")
    search_fields = ("nip", "full_name", "jabatan", "satker", "email")


@admin.register(MasterFacility)
class MasterFacilityAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active", "deleted_at")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "description")


@admin.register(MasterWorkCode)
class MasterWorkCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "default_unit", "is_active", "deleted_at")
    list_filter = ("category", "is_active")
    search_fields = ("code", "name", "default_unit", "description")
