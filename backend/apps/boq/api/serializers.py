"""Serializer BOQ."""
from decimal import Decimal

from rest_framework import serializers

from ..models import BOQItem, BOQRevision


class BOQRevisionSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    item_count = serializers.SerializerMethodField()
    leaf_count = serializers.SerializerMethodField()
    total_pre_ppn = serializers.SerializerMethodField()
    approved_by_username = serializers.CharField(
        source="approved_by.username", read_only=True, default=None,
    )

    class Meta:
        model = BOQRevision
        fields = [
            "id", "contract", "version", "status", "status_display",
            "is_active", "addendum",
            "approved_at", "approved_by", "approved_by_username",
            "notes",
            "item_count", "leaf_count", "total_pre_ppn",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "version", "status", "status_display", "is_active",
            "approved_at", "approved_by", "approved_by_username",
            "item_count", "leaf_count", "total_pre_ppn",
            "created_at", "updated_at",
        ]

    def get_item_count(self, obj: BOQRevision) -> int:
        return obj.items.count()

    def get_leaf_count(self, obj: BOQRevision) -> int:
        return obj.items.filter(is_leaf=True).count()

    def get_total_pre_ppn(self, obj: BOQRevision) -> str:
        from django.db.models import Sum
        agg = obj.items.filter(is_leaf=True).aggregate(t=Sum("total_price"))
        return str((agg["t"] or Decimal("0")).quantize(Decimal("0.01")))


class BOQItemSerializer(serializers.ModelSerializer):
    facility_code = serializers.CharField(source="facility.code", read_only=True)
    facility_name = serializers.CharField(source="facility.name", read_only=True)
    change_type_display = serializers.CharField(source="get_change_type_display", read_only=True)

    class Meta:
        model = BOQItem
        fields = [
            "id", "boq_revision", "facility", "facility_code", "facility_name",
            "code", "full_code", "description", "unit",
            "volume", "unit_price", "total_price", "weight_pct",
            "parent", "level", "display_order", "is_leaf",
            "source_item", "change_type", "change_type_display",
            "old_description", "old_unit",
            "planned_start_week", "planned_duration_weeks",
            "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "facility_code", "facility_name",
            "full_code", "level", "is_leaf",
            "total_price",  # selalu dihitung server-side
            "weight_pct",
            "change_type_display",
            "created_at", "updated_at",
        ]


class BOQItemBulkUpsertItemSerializer(serializers.Serializer):
    """Single item dalam bulk-upsert. id=null/missing => create."""
    id = serializers.UUIDField(required=False, allow_null=True)
    facility = serializers.UUIDField()
    code = serializers.CharField(max_length=40)
    description = serializers.CharField(allow_blank=True)
    unit = serializers.CharField(max_length=30, allow_blank=True, required=False)
    volume = serializers.DecimalField(max_digits=18, decimal_places=4, required=False, default=Decimal("0"))
    unit_price = serializers.DecimalField(max_digits=18, decimal_places=2, required=False, default=Decimal("0"))
    parent = serializers.UUIDField(required=False, allow_null=True)
    display_order = serializers.IntegerField(required=False, default=0)
    planned_start_week = serializers.IntegerField(required=False, allow_null=True)
    planned_duration_weeks = serializers.IntegerField(required=False, allow_null=True)
    notes = serializers.CharField(allow_blank=True, required=False)


class BOQItemBulkSerializer(serializers.Serializer):
    """body.upsert: list item; body.delete_ids: list UUID."""
    upsert = BOQItemBulkUpsertItemSerializer(many=True, required=False)
    delete_ids = serializers.ListField(child=serializers.UUIDField(), required=False)


class BudgetCheckSerializer(serializers.Serializer):
    boq_pre_ppn = serializers.CharField()
    ppn_pct = serializers.CharField()
    ppn_amount = serializers.CharField()
    boq_post_ppn = serializers.CharField()
    nilai_kontrak = serializers.CharField()
    gap = serializers.CharField()
    ok = serializers.BooleanField()
    tolerance = serializers.CharField()
