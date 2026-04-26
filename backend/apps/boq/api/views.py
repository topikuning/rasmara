"""ViewSet BOQ."""
from decimal import Decimal
from io import BytesIO

from django.db import transaction
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
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
from ..services_io.comparison import compare_revisions, export_compare_xlsx
from ..services_io.excel_export import export_revision_xlsx
from ..services_io.excel_import import (
    build_template_workbook,
    check_facility_mapping,
    commit_import,
    parse_excel,
)
from ..services_io.pdf_export import export_revision_pdf
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
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        action_to_perm = {
            "approve": "boq.approve",
            "validate_budget": "boq.read",
            "recompute": "boq.update",
            "import_preview": "boq.import",
            "import_commit": "boq.import",
            "import_template": "boq.read",
            "export_xlsx": "boq.read",
            "export_pdf": "boq.read",
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

    # ---------- Import Excel ----------
    @action(detail=False, methods=["get"], url_path="import-template", pagination_class=None)
    def import_template(self, request):
        """GET /boq-revisions/import-template/  -> Excel template Format A."""
        wb = build_template_workbook()
        buf = BytesIO()
        wb.save(buf)
        resp = HttpResponse(
            buf.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resp["Content-Disposition"] = 'attachment; filename="template-boq.xlsx"'
        return resp

    @action(detail=True, methods=["post"], url_path="import-preview",
            parser_classes=[MultiPartParser, FormParser])
    def import_preview(self, request, pk=None):
        """POST /boq-revisions/{id}/import-preview/  body: file=<excel>

        Parse file, validasi, return preview tanpa commit. Server JANGAN simpan
        file — klien upload ulang saat commit (lebih sederhana, tidak butuh staging).
        """
        rev = self.get_object()
        f = request.FILES.get("file")
        if not f:
            return Response({"error": {"code": "FILE_REQUIRED",
                                        "message": "Field 'file' (Excel) wajib."}}, status=400)
        try:
            rows, preview = parse_excel(f)
        except Exception as e:  # noqa: BLE001
            return Response({"error": {"code": "PARSE_ERROR",
                                        "message": str(e)}}, status=400)

        unmatched = check_facility_mapping(rows, rev)
        preview.unmatched_facility_codes = unmatched

        return Response({
            "detected_format": preview.detected_format,
            "sheet_used": preview.sheet_used,
            "rows_total": preview.rows_total,
            "rows_valid": preview.rows_valid,
            "rows_invalid": preview.rows_invalid,
            "facility_summary": preview.facility_summary,
            "unmatched_facility_codes": preview.unmatched_facility_codes,
            "sample_errors": preview.sample_errors,
            "warnings": preview.warnings,
        })

    @action(detail=True, methods=["post"], url_path="import-commit",
            parser_classes=[MultiPartParser, FormParser])
    def import_commit(self, request, pk=None):
        """POST /boq-revisions/{id}/import-commit/  body: file=<excel>, replace=1

        Parse + commit ke DB. Atomic. Replace existing items by default.
        """
        rev = self.get_object()
        assert_revision_writable(rev)
        f = request.FILES.get("file")
        if not f:
            return Response({"error": {"code": "FILE_REQUIRED",
                                        "message": "Field 'file' wajib."}}, status=400)
        replace = request.data.get("replace", "1") in ("1", "true", "True", "yes")
        try:
            rows, _ = parse_excel(f)
            result = commit_import(rows, rev, replace_existing=replace)
        except Exception as e:  # noqa: BLE001
            return Response({"error": {"code": "IMPORT_ERROR",
                                        "message": str(e)}}, status=400)
        return Response({"detail": "Import selesai.", **result})

    # ---------- Export ----------
    @action(detail=True, methods=["get"], url_path="export-xlsx", pagination_class=None)
    def export_xlsx(self, request, pk=None):
        rev = self.get_object()
        data = export_revision_xlsx(rev)
        resp = HttpResponse(
            data,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        fname = f"BOQ-{rev.contract.number}-V{rev.version}.xlsx".replace("/", "-")
        resp["Content-Disposition"] = f'attachment; filename="{fname}"'
        return resp

    @action(detail=True, methods=["get"], url_path="export-pdf", pagination_class=None)
    def export_pdf(self, request, pk=None):
        rev = self.get_object()
        data = export_revision_pdf(rev)
        resp = HttpResponse(data, content_type="application/pdf")
        fname = f"BOQ-{rev.contract.number}-V{rev.version}.pdf".replace("/", "-")
        resp["Content-Disposition"] = f'attachment; filename="{fname}"'
        return resp


# ====================== Comparison ======================
class BOQCompareView(viewsets.ViewSet):
    """Komparasi antar revisi BOQ.

    GET /api/v1/contracts/{contract_id}/boq-compare/?from=<rev_id>&to=<rev_id>
    """

    permission_classes = (IsAuthenticated, HasPermissionCode)
    required_permission = "boq.read"

    def _resolve(self, request, contract_id: str) -> tuple[BOQRevision, BOQRevision]:
        from common.exceptions import DomainError

        try:
            contract = Contract.objects.get(pk=contract_id)
        except Contract.DoesNotExist:
            raise DomainError("Kontrak tidak ditemukan.", code="NOT_FOUND", status_code=404)

        # Scope check
        user = request.user
        if not user.is_superuser and user.assigned_contract_ids is not None:
            if str(contract.id) not in {str(x) for x in user.assigned_contract_ids}:
                raise DomainError("Tidak punya akses kontrak ini.",
                                  code="PERMISSION_DENIED", status_code=403)

        from_id = request.query_params.get("from")
        to_id = request.query_params.get("to")
        if not from_id or not to_id:
            raise DomainError("Query 'from' dan 'to' (revision IDs) wajib.",
                              code="VALIDATION_ERROR")
        try:
            rev_a = BOQRevision.objects.get(pk=from_id, contract=contract)
            rev_b = BOQRevision.objects.get(pk=to_id, contract=contract)
        except BOQRevision.DoesNotExist:
            raise DomainError("Revisi tidak ditemukan utk kontrak ini.",
                              code="NOT_FOUND", status_code=404)
        return rev_a, rev_b

    def list(self, request, contract_id=None):
        rev_a, rev_b = self._resolve(request, contract_id)
        result = compare_revisions(rev_a, rev_b)
        return Response({
            "revision_a": result.revision_a,
            "revision_b": result.revision_b,
            "lines": [
                {
                    "full_code": ln.full_code,
                    "description": ln.description,
                    "facility_code": ln.facility_code,
                    "unit": ln.unit,
                    "unit_price_a": str(ln.unit_price_a),
                    "unit_price_b": str(ln.unit_price_b),
                    "volume_a": str(ln.volume_a),
                    "volume_b": str(ln.volume_b),
                    "total_a": str(ln.total_a),
                    "total_b": str(ln.total_b),
                    "diff_volume": str(ln.diff_volume),
                    "diff_total": str(ln.diff_total),
                    "note": ln.note,
                }
                for ln in result.lines
            ],
            "total_a": str(result.total_a),
            "total_b": str(result.total_b),
            "total_tambah": str(result.total_tambah),
            "total_kurang": str(result.total_kurang),
        })

    @action(detail=False, methods=["get"], url_path="export-xlsx", pagination_class=None)
    def export_xlsx(self, request, contract_id=None):
        rev_a, rev_b = self._resolve(request, contract_id)
        result = compare_revisions(rev_a, rev_b)
        data = export_compare_xlsx(result, rev_a.contract)
        resp = HttpResponse(
            data,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        fname = (f"Komparasi-BOQ-V{rev_a.version}-vs-V{rev_b.version}-"
                  f"{rev_a.contract.number}.xlsx").replace("/", "-")
        resp["Content-Disposition"] = f'attachment; filename="{fname}"'
        return resp


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
