"""Serializers master data."""
from rest_framework import serializers

from ..models import Company, MasterFacility, MasterWorkCode, PPK


class CompanySerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    default_user_username = serializers.CharField(
        source="default_user.username", read_only=True, default=None,
    )

    class Meta:
        model = Company
        fields = [
            "id", "code", "name", "npwp", "type", "type_display",
            "address", "phone", "email", "pic_name", "pic_phone",
            "default_user", "default_user_username",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "type_display", "default_user", "default_user_username",
            "created_at", "updated_at",
        ]


class CompanyLookupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "code", "name", "type"]


class PPKSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True, default=None)
    user_full_name = serializers.CharField(source="user.full_name", read_only=True, default=None)

    class Meta:
        model = PPK
        fields = [
            "id", "nip", "full_name", "jabatan", "satker",
            "whatsapp", "email",
            "user", "user_username", "user_full_name",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "user", "user_username", "user_full_name",
                            "created_at", "updated_at"]


class PPKLookupSerializer(serializers.ModelSerializer):
    class Meta:
        model = PPK
        fields = ["id", "nip", "full_name", "jabatan"]


class MasterFacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterFacility
        fields = ["id", "code", "name", "description", "is_active",
                   "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class MasterWorkCodeSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = MasterWorkCode
        fields = ["id", "code", "name", "category", "category_display",
                   "default_unit", "description", "is_active",
                   "created_at", "updated_at"]
        read_only_fields = ["id", "category_display", "created_at", "updated_at"]
