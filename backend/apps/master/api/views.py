"""ViewSet master data."""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.permissions import HasPermissionCode

from ..models import Company, MasterFacility, MasterWorkCode, PPK
from ..services import provision_company_user, provision_ppk_user
from .serializers import (
    CompanyLookupSerializer,
    CompanySerializer,
    MasterFacilitySerializer,
    MasterWorkCodeSerializer,
    PPKLookupSerializer,
    PPKSerializer,
)


class _PermViewSet(viewsets.ModelViewSet):
    """Helper: pasang required_permission per action.

    Subclass set MODULE = 'company' / 'ppk' / 'master'.
    """

    permission_classes = (IsAuthenticated, HasPermissionCode)
    MODULE: str = ""

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        action_to_perm = {
            "list": f"{self.MODULE}.read",
            "retrieve": f"{self.MODULE}.read",
            "lookup": f"{self.MODULE}.read",
            "create": f"{self.MODULE}.create",
            "update": f"{self.MODULE}.update",
            "partial_update": f"{self.MODULE}.update",
            "destroy": f"{self.MODULE}.delete",
        }
        self.required_permission = action_to_perm.get(self.action, f"{self.MODULE}.read")


# ---------- Company ----------
class CompanyViewSet(_PermViewSet):
    queryset = Company.objects.all().select_related("default_user").order_by("name")
    serializer_class = CompanySerializer
    MODULE = "company"
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    search_fields = ["code", "name", "npwp", "pic_name", "pic_phone", "email"]
    filterset_fields = ["type"]
    ordering_fields = ["name", "code", "created_at"]

    def perform_destroy(self, instance: Company) -> None:
        # soft-delete (Inv. 12)
        instance.soft_delete(user=getattr(self.request, "user", None))

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        company: Company = s.save(created_by=request.user, updated_by=request.user)

        # Auto-provision user (Inv. 15)
        try:
            user, plain_pwd = provision_company_user(company)
        except Exception:  # noqa: BLE001
            user, plain_pwd = None, ""

        out = self.get_serializer(company).data
        if user is not None and plain_pwd:
            out["initial_user"] = {
                "username": user.username,
                "initial_password": plain_pwd,
                "must_change_password": True,
            }
        return Response(out, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="lookup",
            pagination_class=None)
    def lookup(self, request):
        qs = self.filter_queryset(self.get_queryset())[:50]
        return Response(CompanyLookupSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="reset-default-user-password")
    def reset_default_user_password(self, request, pk=None):
        company = self.get_object()
        if not request.user.has_perm_code("company.update"):
            return Response({"error": {"code": "PERMISSION_DENIED",
                                        "message": "Membutuhkan company.update"}},
                            status=403)
        if company.default_user_id is None:
            user, plain_pwd = provision_company_user(company)
        else:
            from ..services import _generate_password
            plain_pwd = _generate_password()
            company.default_user.set_password(plain_pwd)
            company.default_user.must_change_password = True
            company.default_user.save(
                update_fields=["password", "must_change_password", "updated_at"]
            )
            user = company.default_user
        return Response({
            "username": user.username,
            "initial_password": plain_pwd,
            "must_change_password": True,
        })


# ---------- PPK ----------
class PPKViewSet(_PermViewSet):
    queryset = PPK.objects.all().select_related("user").order_by("full_name")
    serializer_class = PPKSerializer
    MODULE = "ppk"
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    search_fields = ["nip", "full_name", "jabatan", "satker", "whatsapp", "email"]
    ordering_fields = ["full_name", "nip", "created_at"]

    def perform_destroy(self, instance: PPK) -> None:
        instance.soft_delete(user=getattr(self.request, "user", None))

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        ppk: PPK = s.save(created_by=request.user, updated_by=request.user)

        try:
            user, plain_pwd = provision_ppk_user(ppk)
        except Exception:  # noqa: BLE001
            user, plain_pwd = None, ""

        out = self.get_serializer(ppk).data
        if user is not None and plain_pwd:
            out["initial_user"] = {
                "username": user.username,
                "initial_password": plain_pwd,
                "must_change_password": True,
            }
        return Response(out, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="lookup",
            pagination_class=None)
    def lookup(self, request):
        qs = self.filter_queryset(self.get_queryset())[:50]
        return Response(PPKLookupSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="reset-user-password")
    def reset_user_password(self, request, pk=None):
        ppk = self.get_object()
        if not request.user.has_perm_code("ppk.update"):
            return Response({"error": {"code": "PERMISSION_DENIED",
                                        "message": "Membutuhkan ppk.update"}},
                            status=403)
        if ppk.user_id is None:
            user, plain_pwd = provision_ppk_user(ppk)
        else:
            from ..services import _generate_password
            plain_pwd = _generate_password()
            ppk.user.set_password(plain_pwd)
            ppk.user.must_change_password = True
            ppk.user.save(update_fields=["password", "must_change_password", "updated_at"])
            user = ppk.user
        return Response({
            "username": user.username,
            "initial_password": plain_pwd,
            "must_change_password": True,
        })


# ---------- MasterFacility ----------
class MasterFacilityViewSet(_PermViewSet):
    queryset = MasterFacility.objects.all().order_by("name")
    serializer_class = MasterFacilitySerializer
    MODULE = "master"
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    search_fields = ["code", "name", "description"]
    filterset_fields = ["is_active"]
    ordering_fields = ["name", "code", "created_at"]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        # master.read utk read; master.update utk write
        if self.action in ("create", "update", "partial_update", "destroy"):
            self.required_permission = "master.update"
        else:
            self.required_permission = "master.read"

    def perform_destroy(self, instance: MasterFacility) -> None:
        instance.soft_delete(user=getattr(self.request, "user", None))

    @action(detail=False, methods=["get"], url_path="lookup",
            pagination_class=None)
    def lookup(self, request):
        qs = self.filter_queryset(self.get_queryset().filter(is_active=True))[:50]
        return Response(MasterFacilitySerializer(qs, many=True).data)


# ---------- MasterWorkCode ----------
class MasterWorkCodeViewSet(_PermViewSet):
    queryset = MasterWorkCode.objects.all().order_by("category", "code")
    serializer_class = MasterWorkCodeSerializer
    MODULE = "master"
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    search_fields = ["code", "name", "default_unit", "description"]
    filterset_fields = ["category", "is_active"]
    ordering_fields = ["code", "name", "category", "created_at"]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if self.action in ("create", "update", "partial_update", "destroy"):
            self.required_permission = "master.update"
        else:
            self.required_permission = "master.read"

    def perform_destroy(self, instance: MasterWorkCode) -> None:
        instance.soft_delete(user=getattr(self.request, "user", None))

    @action(detail=False, methods=["get"], url_path="lookup",
            pagination_class=None)
    def lookup(self, request):
        qs = self.filter_queryset(self.get_queryset().filter(is_active=True))[:50]
        return Response(MasterWorkCodeSerializer(qs, many=True).data)
