"""Serializer VO + Addendum + FieldObservation."""
from rest_framework import serializers

from ..models import (
    Addendum,
    AddendumVO,
    FieldObservation,
    FieldObservationPhoto,
    VariationOrder,
    VOItem,
)


# ====================== VO ======================
class VOItemSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source="get_action_display", read_only=True)
    source_full_code = serializers.CharField(
        source="source_boq_item.full_code", read_only=True, default=None,
    )
    source_description = serializers.CharField(
        source="source_boq_item.description", read_only=True, default=None,
    )
    facility_code = serializers.CharField(
        source="facility.code", read_only=True, default=None,
    )

    class Meta:
        model = VOItem
        fields = [
            "id", "vo", "action", "action_display",
            "source_boq_item", "source_full_code", "source_description",
            "facility", "facility_code", "parent_boq_item",
            "code", "description", "unit",
            "new_description", "new_unit",
            "volume_delta", "unit_price",
            "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "action_display", "source_full_code",
                             "source_description", "facility_code",
                             "created_at", "updated_at"]


class VariationOrderListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    item_count = serializers.IntegerField(source="items.count", read_only=True)

    class Meta:
        model = VariationOrder
        fields = ["id", "contract", "number", "title", "status", "status_display",
                   "item_count", "created_at", "updated_at"]


class VariationOrderDetailSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    items = VOItemSerializer(many=True, read_only=True)
    submitted_by_username = serializers.CharField(source="submitted_by.username", read_only=True, default=None)
    approved_by_username = serializers.CharField(source="approved_by.username", read_only=True, default=None)
    rejected_by_username = serializers.CharField(source="rejected_by.username", read_only=True, default=None)

    class Meta:
        model = VariationOrder
        fields = [
            "id", "contract", "number", "title", "justification",
            "status", "status_display",
            "submitted_at", "submitted_by", "submitted_by_username",
            "reviewed_at", "reviewed_by",
            "approved_at", "approved_by", "approved_by_username",
            "rejected_at", "rejected_by", "rejected_by_username",
            "rejection_reason",
            "notes",
            "items",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "status", "status_display",
            "submitted_at", "submitted_by", "submitted_by_username",
            "reviewed_at", "reviewed_by",
            "approved_at", "approved_by", "approved_by_username",
            "rejected_at", "rejected_by", "rejected_by_username",
            "rejection_reason",
            "items",
            "created_at", "updated_at",
        ]


class VOActionSerializer(serializers.Serializer):
    """Body utk reject."""
    reason = serializers.CharField(required=False, allow_blank=True)


# ====================== Addendum ======================
class AddendumListSerializer(serializers.ModelSerializer):
    addendum_type_display = serializers.CharField(source="get_addendum_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    vo_count = serializers.SerializerMethodField()

    class Meta:
        model = Addendum
        fields = ["id", "contract", "number", "addendum_type", "addendum_type_display",
                   "status", "status_display",
                   "value_delta", "days_delta",
                   "signed_at", "vo_count",
                   "created_at", "updated_at"]

    def get_vo_count(self, obj: Addendum) -> int:
        return obj.vos.count()


class AddendumDetailSerializer(serializers.ModelSerializer):
    addendum_type_display = serializers.CharField(source="get_addendum_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    vos = VariationOrderListSerializer(many=True, read_only=True)
    signed_by_username = serializers.CharField(source="signed_by.username", read_only=True, default=None)
    needs_kpa = serializers.SerializerMethodField()
    has_kpa = serializers.SerializerMethodField()

    class Meta:
        model = Addendum
        fields = [
            "id", "contract", "number", "addendum_type", "addendum_type_display",
            "reason",
            "status", "status_display",
            "value_delta", "days_delta", "new_end_date",
            "signed_at", "signed_by", "signed_by_username",
            "document",
            "kpa_approval", "needs_kpa", "has_kpa",
            "vos",
            "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "addendum_type_display", "status", "status_display",
            "signed_at", "signed_by", "signed_by_username",
            "needs_kpa", "has_kpa", "vos",
            "created_at", "updated_at",
        ]

    def get_needs_kpa(self, obj: Addendum) -> bool:
        from django.conf import settings
        from decimal import Decimal
        if obj.value_delta == 0:
            return False
        threshold_pct = Decimal(str(settings.RASMARA["KPA_THRESHOLD_PCT"]))
        threshold = obj.contract.original_value * threshold_pct / Decimal("100")
        return abs(obj.value_delta) > threshold

    def get_has_kpa(self, obj: Addendum) -> bool:
        return bool(obj.kpa_approval)


class AddendumBundleSerializer(serializers.Serializer):
    vo_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


class KPAApprovalSerializer(serializers.Serializer):
    signed_by_name = serializers.CharField(max_length=200)
    signed_by_nip = serializers.CharField(max_length=30, required=False, allow_blank=True)
    signed_at = serializers.DateField()
    document_url = serializers.URLField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


# ====================== Field Observation ======================
class FieldObservationPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldObservationPhoto
        fields = ["id", "observation", "file", "thumbnail", "caption",
                   "taken_at", "uploaded_by", "created_at"]
        read_only_fields = ["id", "thumbnail", "uploaded_by", "created_at"]


class FieldObservationSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    location_code = serializers.CharField(source="location.code", read_only=True, default=None)
    photos = FieldObservationPhotoSerializer(many=True, read_only=True)
    photo_count = serializers.IntegerField(source="photos.count", read_only=True)

    class Meta:
        model = FieldObservation
        fields = [
            "id", "contract", "type", "type_display",
            "location", "location_code",
            "observed_at", "notes", "document",
            "submitted_by",
            "photos", "photo_count",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "type_display", "location_code", "submitted_by",
            "photos", "photo_count",
            "created_at", "updated_at",
        ]
