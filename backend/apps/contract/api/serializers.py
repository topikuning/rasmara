"""Serializers Kontrak / Lokasi / Fasilitas."""
from decimal import Decimal

from rest_framework import serializers

from ..models import Contract, ContractStatus, Facility, Location


class FacilityLiteSerializer(serializers.ModelSerializer):
    master_facility_name = serializers.CharField(
        source="master_facility.name", read_only=True,
    )

    class Meta:
        model = Facility
        fields = ["id", "code", "name", "master_facility", "master_facility_name",
                   "display_order"]
        read_only_fields = ["id", "master_facility_name"]


class FacilitySerializer(serializers.ModelSerializer):
    master_facility_name = serializers.CharField(source="master_facility.name", read_only=True)
    master_facility_code = serializers.CharField(source="master_facility.code", read_only=True)
    location_code = serializers.CharField(source="location.code", read_only=True)
    contract_id = serializers.UUIDField(source="location.contract_id", read_only=True)

    class Meta:
        model = Facility
        fields = ["id", "location", "location_code", "contract_id",
                   "code", "master_facility", "master_facility_code", "master_facility_name",
                   "name", "display_order", "notes",
                   "created_at", "updated_at"]
        read_only_fields = ["id", "location_code", "contract_id",
                             "master_facility_code", "master_facility_name",
                             "created_at", "updated_at"]


class LocationLiteSerializer(serializers.ModelSerializer):
    facility_count = serializers.IntegerField(source="facilities.count", read_only=True)
    has_coordinates = serializers.BooleanField(read_only=True)

    class Meta:
        model = Location
        fields = ["id", "code", "name_desa", "name_kecamatan", "name_kota",
                   "name_provinsi", "latitude", "longitude", "has_coordinates",
                   "konsultan", "facility_count"]


class LocationSerializer(serializers.ModelSerializer):
    has_coordinates = serializers.BooleanField(read_only=True)
    konsultan_name = serializers.CharField(source="konsultan.name", read_only=True, default=None)
    facilities = FacilityLiteSerializer(many=True, read_only=True)

    class Meta:
        model = Location
        fields = ["id", "contract", "code",
                   "name_desa", "name_kecamatan", "name_kota", "name_provinsi",
                   "full_address",
                   "latitude", "longitude", "has_coordinates",
                   "konsultan", "konsultan_name",
                   "notes", "facilities",
                   "created_at", "updated_at"]
        read_only_fields = ["id", "has_coordinates", "konsultan_name",
                             "facilities", "created_at", "updated_at"]


class ContractListSerializer(serializers.ModelSerializer):
    """Versi ringan untuk list / dropdown."""
    ppk_name = serializers.CharField(source="ppk.full_name", read_only=True)
    contractor_name = serializers.CharField(source="contractor.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    location_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Contract
        fields = ["id", "number", "name", "status", "status_display",
                   "ppk", "ppk_name", "contractor", "contractor_name",
                   "fiscal_year", "original_value", "current_value", "ppn_pct",
                   "start_date", "end_date", "duration_days",
                   "location_count",
                   "created_at", "updated_at"]


class ContractDetailSerializer(serializers.ModelSerializer):
    ppk_name = serializers.CharField(source="ppk.full_name", read_only=True)
    ppk_nip = serializers.CharField(source="ppk.nip", read_only=True)
    contractor_name = serializers.CharField(source="contractor.name", read_only=True)
    contractor_code = serializers.CharField(source="contractor.code", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    boq_pre_ppn_value = serializers.SerializerMethodField()
    ppn_amount = serializers.SerializerMethodField()
    is_godmode_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Contract
        fields = ["id", "number", "name",
                   "ppk", "ppk_name", "ppk_nip",
                   "contractor", "contractor_name", "contractor_code",
                   "fiscal_year",
                   "original_value", "current_value", "ppn_pct",
                   "boq_pre_ppn_value", "ppn_amount",
                   "start_date", "end_date", "duration_days",
                   "status", "status_display",
                   "unlock_until", "unlock_reason", "is_godmode_active",
                   "document", "notes",
                   "created_at", "updated_at"]
        read_only_fields = ["id", "ppk_name", "ppk_nip",
                             "contractor_name", "contractor_code",
                             "status_display", "boq_pre_ppn_value", "ppn_amount",
                             "is_godmode_active",
                             "duration_days",
                             "created_at", "updated_at"]

    def get_boq_pre_ppn_value(self, obj: Contract) -> str:
        return str(obj.boq_pre_ppn_value)

    def get_ppn_amount(self, obj: Contract) -> str:
        return str(obj.ppn_amount)

    def validate(self, attrs):
        start = attrs.get("start_date") or (self.instance and self.instance.start_date)
        end = attrs.get("end_date") or (self.instance and self.instance.end_date)
        if start and end and end < start:
            raise serializers.ValidationError(
                {"end_date": "Tanggal selesai tidak boleh sebelum tanggal mulai."}
            )

        # current_value tidak boleh diisi manual saat create — selalu mirror original_value
        if self.instance is None:
            if "current_value" in attrs:
                attrs["current_value"] = attrs.get("original_value", attrs["current_value"])
        return attrs


class GateCheckSerializer(serializers.Serializer):
    code = serializers.CharField()
    label = serializers.CharField()
    ok = serializers.BooleanField()
    detail = serializers.CharField(allow_blank=True)


class GateResultSerializer(serializers.Serializer):
    ok = serializers.BooleanField()
    checks = GateCheckSerializer(many=True)


class GodmodeSerializer(serializers.Serializer):
    hours = serializers.IntegerField(min_value=1, max_value=72)
    reason = serializers.CharField(min_length=8)


class FacilityReorderItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    display_order = serializers.IntegerField(min_value=0)
