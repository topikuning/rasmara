from django.contrib import admin

from .models import BOQItem, BOQRevision


@admin.register(BOQRevision)
class BOQRevisionAdmin(admin.ModelAdmin):
    list_display = ("contract", "version", "status", "is_active", "approved_at", "approved_by")
    list_filter = ("status", "is_active")
    search_fields = ("contract__number", "contract__name")


@admin.register(BOQItem)
class BOQItemAdmin(admin.ModelAdmin):
    list_display = ("full_code", "description", "facility", "level",
                     "is_leaf", "volume", "unit", "unit_price", "total_price",
                     "weight_pct", "change_type")
    list_filter = ("is_leaf", "change_type", "level")
    search_fields = ("code", "full_code", "description")
    raw_id_fields = ("parent", "source_item", "facility", "boq_revision")
