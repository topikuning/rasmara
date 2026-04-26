from django.contrib import admin

from .models import Addendum


@admin.register(Addendum)
class AddendumAdmin(admin.ModelAdmin):
    list_display = ("contract", "number", "addendum_type", "status",
                     "value_delta", "days_delta", "signed_at")
    list_filter = ("status", "addendum_type")
    search_fields = ("number", "contract__number")
