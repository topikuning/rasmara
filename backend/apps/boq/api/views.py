"""ViewSet BOQ."""
from decimal import Decimal

from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.contract.models import Contract
from apps.contract.services import filter_contracts_for_user
from apps.core.permissions import HasPermissionCode

from ..models import BOQItem, BOQRevision, BOQRevisionStatus
from ..services import (
    approve_revision,
    assert_revision_writable,
    delete_item_safe,
    recompute_all,
    recompute_weight_pct,
    validate_budget,
)
from .serializers import (
    BOQItemBulkSerializer,
    BOQItemSerializer,
    BOQRevisionSerializer,
    BudgetCheckSerializer,
)


def _user_can_access_contract(user, contract: Contract) -> bool:
    if user.is_superuser:
        return True
    if user.assigned_contract_ids is None:
        return True
    return str(contract.id) in {str(x) for x in user.assigned_contract_ids}


class BOQRevisionViewSet(viewsets.ReadOnlyModelViewSet):
    """List & detail revisi BOQ. Aksi via @action endpoints."""

    permission_classes = (IsAuthenticated, HasPermissionCode)
    serializer_class = BOQRevisionSerializer
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filterset_fields = ["contract", "status", "is_active"]
    ordering_fields = ["version", "created_at"]
    ordering = ["contract", "version"]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        action_to_perm = {
            "approve": "boq.approve",
            "validate_budget": "boq.read",
            "recompute": "boq.update",
        }
        self.required_permission = action_to_perm.get(self.action, "boq.read")

    def get_queryset(self):
        qs = BOQRevision.objects.select_related("contract", "approved_by")
        user = self.request.user
        if not user.is_superuser and user.assigned_contract_ids is not None:
            qs = qs.filter(contract_id__in=user.assigned_contract_ids)
        return qs

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        rev = self.get_object()
        approve_revision(rev, user=request.user)
        return Response(self.get_serializer(rev).data)

    @action(detail=True, methods=["post"], url_path="validate-budget")
    def validate_budget(self, request, pk=None):
        rev = self.get_object()
        return Response(BudgetCheckSerializer(validate_budget(rev)).data)

    @action(detail=True, methods=["post"])
    def recompute(self, request, pk=None):
        rev = self.get_object()
        assert_revision_writable(rev)
        result = recompute_all(rev)
        return Response({"detail": "Recompute selesai.", **{k: str(v) for k, v in result.items()}})


class BOQItemViewSet(viewsets.ModelViewSet):
    """CRUD item BOQ + bulk upsert."""

    permission_classes = (IsAuthenticated, HasPermissionCode)
    serializer_class = BOQItemSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    search_fields = ["code", "full_code", "description"]
    filterset_fields = ["boq_revision", "facility", "is_leaf", "level", "change_type"]
    ordering_fields = ["display_order", "full_code", "code", "level"]
    ordering = ["facility", "display_order", "full_code"]

    PERM_MAP = {
        "list": "boq.read", "retrieve": "boq.read",
        "create": "boq.update", "update": "boq.update",
        "partial_update": "boq.update", "destroy": "boq.delete",
        "bulk": "boq.update",
    }

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.required_permission = self.PERM_MAP.get(self.action, "boq.read")

    def get_queryset(self):
        qs = BOQItem.objects.select_related("facility", "boq_revision__contract")
        user = self.request.user
        if not user.is_superuser and user.assigned_contract_ids is not None:
            qs = qs.filter(boq_revision__contract_id__in=user.assigned_contract_ids)
        return qs

    @transaction.atomic
    def perform_create(self, serializer):
        rev = serializer.validated_data["boq_revision"]
        assert_revision_writable(rev)
        item = serializer.save()
        # Recompute setelah perubahan
        recompute_all(rev)

    @transaction.atomic
    def perform_update(self, serializer):
        rev = serializer.instance.boq_revision
        assert_revision_writable(rev)
        serializer.save()
        recompute_all(rev)

    @transaction.atomic
    def perform_destroy(self, instance: BOQItem):
        assert_revision_writable(instance.boq_revision)
        delete_item_safe(instance)

    @action(detail=False, methods=["post"], url_path="bulk")
    @transaction.atomic
    def bulk(self, request):
        """Bulk upsert + delete dalam 1 request.

        body: { revision_id, upsert: [items], delete_ids: [uuids] }
        """
        rev_id = request.data.get("revision_id")
        if not rev_id:
            return Response({"error": {"code": "VALIDATION_ERROR",
                                        "message": "revision_id wajib."}}, status=400)
        try:
            rev = BOQRevision.objects.get(pk=rev_id)
        except BOQRevision.DoesNotExist:
            return Response(status=404)
        if not _user_can_access_contract(request.user, rev.contract):
            return Response(status=403)
        assert_revision_writable(rev)

        s = BOQItemBulkSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        upsert_data = s.validated_data.get("upsert", [])
        delete_ids = s.validated_data.get("delete_ids", [])

        # Delete (safe — clear children parent first)
        for did in delete_ids:
            try:
                it = BOQItem.objects.get(pk=did, boq_revision=rev)
            except BOQItem.DoesNotExist:
                continue
            delete_item_safe(it)

        # Upsert
        created = 0
        updated = 0
        for d in upsert_data:
            iid = d.get("id")
            payload = {
                "code": d["code"],
                "description": d.get("description", ""),
                "unit": d.get("unit", ""),
                "volume": d.get("volume", Decimal("0")),
                "unit_price": d.get("unit_price", Decimal("0")),
                "facility_id": d["facility"],
                "parent_id": d.get("parent"),
                "display_order": d.get("display_order", 0),
                "planned_start_week": d.get("planned_start_week"),
                "planned_duration_weeks": d.get("planned_duration_weeks"),
                "notes": d.get("notes", ""),
            }
            if iid:
                BOQItem.objects.filter(pk=iid, boq_revision=rev).update(**payload)
                updated += 1
            else:
                BOQItem.objects.create(boq_revision=rev, **payload)
                created += 1

        recompute_all(rev)
        return Response({
            "detail": "OK", "created": created, "updated": updated,
            "deleted": len(delete_ids),
        })
