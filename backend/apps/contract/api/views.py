"""ViewSet Kontrak / Lokasi / Fasilitas."""
from django.db import transaction
from django.db.models import Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.permissions import HasPermissionCode

from ..models import Contract, ContractStatus, Facility, Location
from ..services import (
    clear_godmode,
    evaluate_activation_gates,
    filter_contracts_for_user,
    is_user_in_scope,
    recalc_duration,
    set_godmode,
    transition,
)
from .serializers import (
    ContractDetailSerializer,
    ContractListSerializer,
    FacilityReorderItemSerializer,
    FacilitySerializer,
    GateResultSerializer,
    GodmodeSerializer,
    LocationLiteSerializer,
    LocationSerializer,
)


# ======================== Contract ========================
class ContractViewSet(viewsets.ModelViewSet):
    """CRUD kontrak + state actions."""

    permission_classes = (IsAuthenticated, HasPermissionCode)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    search_fields = ["number", "name"]
    filterset_fields = ["status", "fiscal_year", "ppk", "contractor"]
    ordering_fields = ["fiscal_year", "number", "start_date", "end_date",
                        "original_value", "current_value", "created_at"]
    ordering = ["-fiscal_year", "number"]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    PERM_MAP = {
        "list": "contract.read",
        "retrieve": "contract.read",
        "lookup": "contract.read",
        "create": "contract.create",
        "update": "contract.update",
        "partial_update": "contract.update",
        "destroy": "contract.delete",
        "activate": "contract.activate",
        "complete": "contract.complete",
        "terminate": "contract.terminate",
        "hold": "contract.hold",
        "unhold": "contract.hold",
        "evaluate_gates": "contract.read",
        "godmode": "contract.read",  # extra check superuser di method
        "summary": "contract.read",
        "timeline": "contract.read",
    }

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.required_permission = self.PERM_MAP.get(self.action, "contract.read")

    def get_queryset(self):
        qs = (Contract.objects
                .select_related("ppk", "contractor")
                .annotate(location_count=Count("locations",
                                                  filter=Q(locations__deleted_at__isnull=True)))
              )
        return filter_contracts_for_user(qs, self.request.user)

    def get_serializer_class(self):
        if self.action in ("list", "lookup"):
            return ContractListSerializer
        return ContractDetailSerializer

    def perform_create(self, serializer):
        contract = serializer.save(
            created_by=self.request.user, updated_by=self.request.user,
            current_value=serializer.validated_data.get("original_value"),
        )
        recalc_duration(contract)
        contract.save(update_fields=["duration_days", "updated_at"])

    def perform_update(self, serializer):
        contract = serializer.save(updated_by=self.request.user)
        recalc_duration(contract)
        contract.save(update_fields=["duration_days", "updated_at"])

    def perform_destroy(self, instance: Contract):
        instance.soft_delete(user=self.request.user)

    @action(detail=False, methods=["get"], url_path="lookup", pagination_class=None)
    def lookup(self, request):
        qs = self.filter_queryset(self.get_queryset())[:50]
        return Response(ContractListSerializer(qs, many=True).data)

    @action(detail=True, methods=["get"], url_path="evaluate-gates")
    def evaluate_gates(self, request, pk=None):
        contract = self.get_object()
        result = evaluate_activation_gates(contract)
        return Response(GateResultSerializer({
            "ok": result.ok,
            "checks": [{"code": c.code, "label": c.label, "ok": c.ok, "detail": c.detail}
                        for c in result.checks],
        }).data)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        contract = self.get_object()
        bypass = bool(request.data.get("bypass_gate"))
        if bypass and not request.user.is_superuser:
            return Response({"error": {"code": "PERMISSION_DENIED",
                                        "message": "bypass_gate hanya untuk superadmin."}},
                            status=403)
        transition(contract, ContractStatus.ACTIVE, user=request.user, bypass_gate=bypass)
        return Response(ContractDetailSerializer(contract, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        contract = self.get_object()
        transition(contract, ContractStatus.COMPLETED, user=request.user)
        return Response(ContractDetailSerializer(contract, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def terminate(self, request, pk=None):
        contract = self.get_object()
        transition(contract, ContractStatus.TERMINATED, user=request.user)
        return Response(ContractDetailSerializer(contract, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def hold(self, request, pk=None):
        contract = self.get_object()
        transition(contract, ContractStatus.ON_HOLD, user=request.user)
        return Response(ContractDetailSerializer(contract, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def unhold(self, request, pk=None):
        contract = self.get_object()
        transition(contract, ContractStatus.ACTIVE, user=request.user)
        return Response(ContractDetailSerializer(contract, context={"request": request}).data)

    @action(detail=True, methods=["post", "delete"])
    def godmode(self, request, pk=None):
        contract = self.get_object()
        if not request.user.is_superuser:
            return Response({"error": {"code": "PERMISSION_DENIED",
                                        "message": "Godmode hanya untuk superadmin."}},
                            status=403)
        if request.method == "DELETE":
            clear_godmode(contract, user=request.user)
        else:
            s = GodmodeSerializer(data=request.data)
            s.is_valid(raise_exception=True)
            set_godmode(contract, hours=s.validated_data["hours"],
                        reason=s.validated_data["reason"], user=request.user)
        return Response(ContractDetailSerializer(contract, context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def summary(self, request, pk=None):
        """Header ringkas: nilai breakdown PPN, count lokasi/fasilitas, gates."""
        contract = self.get_object()
        gates = evaluate_activation_gates(contract)
        return Response({
            "id": str(contract.pk),
            "number": contract.number,
            "name": contract.name,
            "status": contract.status,
            "status_display": contract.get_status_display(),
            "fiscal_year": contract.fiscal_year,
            "ppn_pct": str(contract.ppn_pct),
            "original_value": str(contract.original_value),
            "current_value": str(contract.current_value),
            "boq_pre_ppn_value": str(contract.boq_pre_ppn_value),
            "ppn_amount": str(contract.ppn_amount),
            "start_date": contract.start_date,
            "end_date": contract.end_date,
            "duration_days": contract.duration_days,
            "location_count": contract.locations.alive().count(),
            "facility_count": Facility.objects.filter(
                location__contract=contract, deleted_at__isnull=True,
                location__deleted_at__isnull=True,
            ).count(),
            "is_godmode_active": contract.is_godmode_active,
            "gates_ok": gates.ok,
            "gates_failed_count": len(gates.failed),
        })

    @action(detail=True, methods=["get"])
    def timeline(self, request, pk=None):
        """Timeline kontrak: V0 -> Addendum 1 (V1) -> ..."""
        contract = self.get_object()
        events: list[dict] = [{
            "kind": "CREATED",
            "label": "Kontrak dibuat",
            "date": contract.created_at,
            "detail": f"Nilai awal Rp {contract.original_value:,.2f}",
        }]
        # BOQ V0 + addenda akan ditambah saat modul 4-5 aktif
        try:
            from apps.boq.models import BOQRevision  # noqa: F401
            from django.apps import apps as django_apps
            BoqRev = django_apps.get_model("boq", "BOQRevision")
            for rev in BoqRev.objects.filter(contract=contract).order_by("version"):
                events.append({
                    "kind": "BOQ_REVISION",
                    "label": f"BOQ V{rev.version}",
                    "date": rev.approved_at or rev.created_at,
                    "detail": rev.get_status_display(),
                })
        except (ImportError, LookupError):
            pass
        return Response({"events": events})


# ======================== Location ========================
class LocationViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated, HasPermissionCode)
    serializer_class = LocationSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    search_fields = ["code", "name_desa", "name_kecamatan", "name_kota", "name_provinsi"]
    filterset_fields = ["contract", "konsultan"]
    ordering_fields = ["code", "name_kota", "created_at"]

    PERM_MAP = {
        "list": "location.read", "retrieve": "location.read",
        "create": "location.create", "update": "location.update",
        "partial_update": "location.update", "destroy": "location.delete",
    }

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.required_permission = self.PERM_MAP.get(self.action, "location.read")

    def get_queryset(self):
        qs = (Location.objects
                .select_related("contract", "konsultan")
                .prefetch_related("facilities"))
        # Scope by contract
        user = self.request.user
        if not user.is_authenticated:
            return qs.none()
        if not user.is_superuser and user.assigned_contract_ids is not None:
            qs = qs.filter(contract_id__in=user.assigned_contract_ids)
        return qs

    def perform_destroy(self, instance: Location):
        instance.soft_delete(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


# ======================== Facility ========================
class FacilityViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated, HasPermissionCode)
    serializer_class = FacilitySerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    search_fields = ["code", "name"]
    filterset_fields = ["location", "master_facility"]
    ordering_fields = ["display_order", "code", "name", "created_at"]

    PERM_MAP = {
        "list": "facility.read", "retrieve": "facility.read",
        "create": "facility.create", "update": "facility.update",
        "partial_update": "facility.update", "destroy": "facility.delete",
        "reorder": "facility.update",
    }

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.required_permission = self.PERM_MAP.get(self.action, "facility.read")

    def get_queryset(self):
        qs = (Facility.objects
                .select_related("location", "master_facility", "location__contract"))
        user = self.request.user
        if not user.is_authenticated:
            return qs.none()
        if not user.is_superuser and user.assigned_contract_ids is not None:
            qs = qs.filter(location__contract_id__in=user.assigned_contract_ids)
        return qs

    def perform_destroy(self, instance: Facility):
        instance.soft_delete(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def reorder(self, request):
        items = request.data.get("items", [])
        s = FacilityReorderItemSerializer(data=items, many=True)
        s.is_valid(raise_exception=True)
        for it in s.validated_data:
            Facility.objects.filter(pk=it["id"]).update(display_order=it["display_order"])
        return Response({"detail": "OK", "count": len(s.validated_data)})
