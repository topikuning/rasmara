from django.contrib import admin

from .models import (
    Addendum,
    AddendumVO,
    FieldObservation,
    FieldObservationPhoto,
    VariationOrder,
    VOItem,
)


@admin.register(VariationOrder)
class VariationOrderAdmin(admin.ModelAdmin):
    list_display = ("contract", "number", "title", "status", "approved_at")
    list_filter = ("status",)
    search_fields = ("number", "title", "justification")


@admin.register(VOItem)
class VOItemAdmin(admin.ModelAdmin):
    list_display = ("vo", "action", "source_boq_item", "facility", "volume_delta")
    list_filter = ("action",)


@admin.register(Addendum)
class AddendumAdmin(admin.ModelAdmin):
    list_display = ("contract", "number", "addendum_type", "status",
                     "value_delta", "days_delta", "signed_at")
    list_filter = ("status", "addendum_type")
    search_fields = ("number", "reason")


admin.site.register(AddendumVO)


@admin.register(FieldObservation)
class FieldObservationAdmin(admin.ModelAdmin):
    list_display = ("contract", "type", "location", "observed_at")
    list_filter = ("type",)
    search_fields = ("notes",)


admin.site.register(FieldObservationPhoto)
