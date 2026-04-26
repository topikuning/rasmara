"""ViewSet VO + Addendum + FieldObservation."""
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.contract.services import filter_contracts_for_user
from apps.core.permissions import HasPermissionCode

from ..models import (
    Addendum,
    AddendumStatus,
    FieldObservation,
    FieldObservationPhoto,
    VariationOrder,
    VOItem,
    VOStatus,
)
from ..services import (
    _assert_vo_writable,
    addendum_bundle_vo,
    addendum_sign,
    addendum_unbundle_vo,
    vo_approve,
    vo_reject,
    vo_return_to_draft,
    vo_submit,
)
from .serializers import (
    AddendumBundleSerializer,
    AddendumDetailSerializer,
    AddendumListSerializer,
    FieldObservationPhotoSerializer,
    FieldObservationSerializer,
    KPAApprovalSerializer,
    VariationOrderDetailSerializer,
    VariationOrderListSerializer,
    VOActionSerializer,
    VOItemSerializer,
)


# ====================== VO ======================
class VariationOrderViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated, HasPermissionCode)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    search_fields = ["number", "title", "justification"]
    filterset_fields = ["contract", "status"]
    ordering_fields = ["number", "created_at", "approved_at"]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    PERM_MAP = {
        "list": "vo.read", "retrieve": "vo.read",
        "create": "vo.create", "update": "vo.update",
        "partial_update": "vo.update", "destroy": "vo.delete",
        "submit": "vo.submit", "return_to_draft": "vo.update",
        "approve": "vo.approve", "reject": "vo.reject",
    }

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.required_permission = self.PERM_MAP.get(self.action, "vo.read")

    def get_queryset(self):
        qs = VariationOrder.objects.select_related("contract").prefetch_related("items")
        user = self.request.user
        if not user.is_superuser and user.assigned_contract_ids is not None:
            qs = qs.filter(contract_id__in=user.assigned_contract_ids)
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return VariationOrderListSerializer
        return VariationOrderDetailSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        _assert_vo_writable(serializer.instance)
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance: VariationOrder):
        _assert_vo_writable(instance)
        instance.delete()

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        vo = self.get_object()
        vo_submit(vo, user=request.user)
        return Response(VariationOrderDetailSerializer(vo).data)

    @action(detail=True, methods=["post"], url_path="return-to-draft")
    def return_to_draft(self, request, pk=None):
        vo = self.get_object()
        vo_return_to_draft(vo, user=request.user)
        return Response(VariationOrderDetailSerializer(vo).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        vo = self.get_object()
        vo_approve(vo, user=request.user)
        return Response(VariationOrderDetailSerializer(vo).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        vo = self.get_object()
        s = VOActionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        vo_reject(vo, user=request.user, reason=s.validated_data.get("reason", ""))
        return Response(VariationOrderDetailSerializer(vo).data)


class VOItemViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated, HasPermissionCode)
    serializer_class = VOItemSerializer
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filterset_fields = ["vo", "action"]
    ordering = ["created_at"]

    PERM_MAP = {
        "list": "vo.read", "retrieve": "vo.read",
        "create": "vo.update", "update": "vo.update",
        "partial_update": "vo.update", "destroy": "vo.update",
    }

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.required_permission = self.PERM_MAP.get(self.action, "vo.read")

    def get_queryset(self):
        qs = VOItem.objects.select_related(
            "vo", "source_boq_item", "facility", "parent_boq_item",
        )
        user = self.request.user
        if not user.is_superuser and user.assigned_contract_ids is not None:
            qs = qs.filter(vo__contract_id__in=user.assigned_contract_ids)
        return qs

    def perform_create(self, serializer):
        vo = serializer.validated_data["vo"]
        _assert_vo_writable(vo)
        serializer.save()

    def perform_update(self, serializer):
        _assert_vo_writable(serializer.instance.vo)
        serializer.save()

    def perform_destroy(self, instance: VOItem):
        _assert_vo_writable(instance.vo)
        instance.delete()


# ====================== Addendum ======================
class AddendumViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated, HasPermissionCode)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    search_fields = ["number", "reason"]
    filterset_fields = ["contract", "status", "addendum_type"]
    ordering_fields = ["number", "created_at", "signed_at"]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    PERM_MAP = {
        "list": "addendum.read", "retrieve": "addendum.read",
        "create": "addendum.create", "update": "addendum.update",
        "partial_update": "addendum.update", "destroy": "addendum.delete",
        "bundle_vo": "addendum.update", "unbundle_vo": "addendum.update",
        "upload_kpa": "addendum.update",
        "sign": "addendum.sign",
        "preview": "addendum.read",
    }

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.required_permission = self.PERM_MAP.get(self.action, "addendum.read")

    def get_queryset(self):
        qs = Addendum.objects.select_related("contract", "signed_by").prefetch_related("vos")
        user = self.request.user
        if not user.is_superuser and user.assigned_contract_ids is not None:
            qs = qs.filter(contract_id__in=user.assigned_contract_ids)
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return AddendumListSerializer
        return AddendumDetailSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        if serializer.instance.status != AddendumStatus.DRAFT:
            from common.exceptions import DomainError
            raise DomainError("Addendum sudah SIGNED, tidak bisa diedit.",
                              code="ADDENDUM_LOCKED")
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance: Addendum):
        if instance.status != AddendumStatus.DRAFT:
            from common.exceptions import DomainError
            raise DomainError("Addendum sudah SIGNED, tidak bisa dihapus.",
                              code="ADDENDUM_LOCKED")
        instance.delete()

    @action(detail=True, methods=["post"], url_path="bundle-vo")
    def bundle_vo(self, request, pk=None):
        ad = self.get_object()
        s = AddendumBundleSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        addendum_bundle_vo(ad, vo_ids=s.validated_data["vo_ids"], user=request.user)
        return Response(AddendumDetailSerializer(ad).data)

    @action(detail=True, methods=["post"], url_path="unbundle-vo")
    def unbundle_vo(self, request, pk=None):
        ad = self.get_object()
        s = AddendumBundleSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        addendum_unbundle_vo(ad, vo_ids=s.validated_data["vo_ids"], user=request.user)
        return Response(AddendumDetailSerializer(ad).data)

    @action(detail=True, methods=["post"], url_path="upload-kpa-approval")
    def upload_kpa(self, request, pk=None):
        ad = self.get_object()
        if ad.status != AddendumStatus.DRAFT:
            return Response({"error": {"code": "ADDENDUM_LOCKED",
                                        "message": "Addendum sudah SIGNED."}}, status=409)
        s = KPAApprovalSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        ad.kpa_approval = s.validated_data
        ad.save(update_fields=["kpa_approval", "updated_at"])
        return Response(AddendumDetailSerializer(ad).data)

    @action(detail=True, methods=["post"])
    def sign(self, request, pk=None):
        ad = self.get_object()
        addendum_sign(ad, user=request.user)
        return Response(AddendumDetailSerializer(ad).data)

    @action(detail=True, methods=["get"])
    def preview(self, request, pk=None):
        """Preview dampak addendum sebelum sign."""
        from decimal import Decimal
        ad = self.get_object()
        contract = ad.contract
        vos = list(ad.vos.all())
        item_count = sum(v.items.count() for v in vos)

        from django.conf import settings
        threshold_pct = Decimal(str(settings.RASMARA["KPA_THRESHOLD_PCT"]))
        threshold = contract.original_value * threshold_pct / Decimal("100")
        needs_kpa = abs(ad.value_delta) > threshold and ad.value_delta != 0

        return Response({
            "addendum_number": ad.number,
            "addendum_type": ad.addendum_type,
            "status": ad.status,
            "vo_count": len(vos),
            "vo_item_count": item_count,
            "value_delta": str(ad.value_delta),
            "days_delta": ad.days_delta,
            "new_end_date": ad.new_end_date,
            "current_value_before": str(contract.current_value),
            "current_value_after": str(contract.current_value + ad.value_delta),
            "end_date_before": contract.end_date,
            "end_date_after": ad.new_end_date or contract.end_date,
            "needs_kpa": needs_kpa,
            "has_kpa": bool(ad.kpa_approval),
            "kpa_threshold_amount": str(threshold),
            "vo_status_invalid": [
                v.number for v in vos if v.status != VOStatus.APPROVED
            ],
        })


# ====================== Field Observation (MC) ======================
class FieldObservationViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated, HasPermissionCode)
    serializer_class = FieldObservationSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    search_fields = ["notes"]
    filterset_fields = ["contract", "type", "location"]
    ordering_fields = ["observed_at", "created_at"]
    ordering = ["-observed_at"]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    PERM_MAP = {
        "list": "mc.read", "retrieve": "mc.read",
        "create": "mc.create", "update": "mc.update",
        "partial_update": "mc.update", "destroy": "mc.delete",
        "upload_photo": "mc.update",
    }

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.required_permission = self.PERM_MAP.get(self.action, "mc.read")

    def get_queryset(self):
        qs = FieldObservation.objects.select_related(
            "contract", "location", "submitted_by",
        ).prefetch_related("photos")
        user = self.request.user
        if not user.is_superuser and user.assigned_contract_ids is not None:
            qs = qs.filter(contract_id__in=user.assigned_contract_ids)
        return qs

    def perform_create(self, serializer):
        serializer.save(submitted_by=self.request.user, created_by=self.request.user,
                          updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="photos",
            parser_classes=[MultiPartParser, FormParser])
    def upload_photo(self, request, pk=None):
        obs = self.get_object()
        f = request.FILES.get("file")
        if not f:
            return Response({"error": {"code": "FILE_REQUIRED",
                                        "message": "Field 'file' wajib."}}, status=400)
        photo = FieldObservationPhoto.objects.create(
            observation=obs,
            file=f,
            caption=request.data.get("caption", ""),
            uploaded_by=request.user,
        )
        return Response(FieldObservationPhotoSerializer(photo).data, status=201)
