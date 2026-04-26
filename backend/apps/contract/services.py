"""Service Kontrak: state machine, gate aktivasi (Bagian 4 CLAUDE.md), godmode (Inv. 14)."""
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from common.exceptions import DomainError, InvalidStateTransitionError

from .models import Contract, ContractStatus, Facility, Location

# Transisi legal status kontrak.
LEGAL_TRANSITIONS: dict[str, set[str]] = {
    ContractStatus.DRAFT: {ContractStatus.ACTIVE, ContractStatus.TERMINATED},
    ContractStatus.ACTIVE: {ContractStatus.ON_HOLD, ContractStatus.COMPLETED, ContractStatus.TERMINATED},
    ContractStatus.ON_HOLD: {ContractStatus.ACTIVE, ContractStatus.TERMINATED},
    ContractStatus.COMPLETED: set(),    # terminal append-only
    ContractStatus.TERMINATED: set(),   # terminal append-only
}


# ---------- Gate aktivasi ----------
@dataclass
class GateCheck:
    code: str
    label: str
    ok: bool
    detail: str = ""


@dataclass
class GateResult:
    ok: bool
    checks: list[GateCheck] = field(default_factory=list)

    @property
    def failed(self) -> list[GateCheck]:
        return [c for c in self.checks if not c.ok]


def evaluate_activation_gates(contract: Contract) -> GateResult:
    """Evaluasi gate aktivasi DRAFT -> ACTIVE (Bagian 4 CLAUDE.md).

    1. Kontrak punya minimal 1 lokasi dengan koordinat (lat/long).
    2. Setiap lokasi punya minimal 1 fasilitas.
    3. Ada revisi BOQ V0 dengan status APPROVED dan is_active=true.
    4. sum(BOQ leaf) * (1 + ppn/100) <= original_value (toleransi Rp 1).

    Cek #3 dan #4 baru aktif setelah modul BOQ (Modul 4) terpasang.
    Sementara dilewatkan kalau import boq belum ada.
    """
    checks: list[GateCheck] = []

    # ---- Cek 1: minimal 1 lokasi dengan koordinat ----
    locations = Contract.objects.filter(pk=contract.pk).first()
    locs = list(contract.locations.alive())
    if not locs:
        checks.append(GateCheck(
            code="LOCATION_REQUIRED",
            label="Minimal 1 lokasi.",
            ok=False,
            detail="Kontrak belum punya lokasi. Tambah minimal 1 lokasi dengan koordinat.",
        ))
    else:
        loc_no_coord = [l for l in locs if not l.has_coordinates]
        if loc_no_coord:
            checks.append(GateCheck(
                code="COORD_REQUIRED",
                label="Setiap lokasi wajib punya koordinat (lat/long).",
                ok=False,
                detail=f"{len(loc_no_coord)} lokasi belum berkoordinat: " +
                        ", ".join(l.code for l in loc_no_coord[:5]) +
                        ("..." if len(loc_no_coord) > 5 else ""),
            ))
        else:
            checks.append(GateCheck(
                code="LOCATION_REQUIRED",
                label="Minimal 1 lokasi dengan koordinat.",
                ok=True,
                detail=f"{len(locs)} lokasi.",
            ))

    # ---- Cek 2: setiap lokasi minimal 1 fasilitas ----
    if locs:
        loc_no_fac = [l for l in locs if not l.facilities.alive().exists()]
        if loc_no_fac:
            checks.append(GateCheck(
                code="FACILITY_REQUIRED",
                label="Setiap lokasi wajib punya minimal 1 fasilitas.",
                ok=False,
                detail=f"{len(loc_no_fac)} lokasi tanpa fasilitas: " +
                        ", ".join(l.code for l in loc_no_fac[:5]) +
                        ("..." if len(loc_no_fac) > 5 else ""),
            ))
        else:
            total_fac = sum(l.facilities.alive().count() for l in locs)
            checks.append(GateCheck(
                code="FACILITY_REQUIRED",
                label="Setiap lokasi punya fasilitas.",
                ok=True,
                detail=f"{total_fac} fasilitas total.",
            ))

    # ---- Cek 3: BOQ V0 APPROVED + active ----
    try:
        from apps.boq.models import BOQRevision  # type: ignore
        boq = BOQRevision.objects.filter(
            contract=contract, version=0, is_active=True, status="APPROVED",
        ).first()
        if boq is None:
            checks.append(GateCheck(
                code="BOQ_V0_REQUIRED",
                label="Revisi BOQ V0 APPROVED dan aktif wajib ada.",
                ok=False,
                detail="Buat dan approve revisi BOQ V0 sebelum aktivasi.",
            ))
        else:
            checks.append(GateCheck(
                code="BOQ_V0_REQUIRED",
                label="Revisi BOQ V0 aktif.",
                ok=True,
                detail=f"Revisi V0 disetujui pada {boq.approved_at:%d %b %Y}.",
            ))
    except (ImportError, LookupError):
        # Modul BOQ belum terpasang — skip cek (akan ada saat modul 4)
        checks.append(GateCheck(
            code="BOQ_V0_REQUIRED",
            label="Revisi BOQ V0 APPROVED dan aktif wajib ada.",
            ok=False,
            detail="Modul BOQ belum aktif. Akan dicek setelah modul BOQ dipasang.",
        ))

    # ---- Cek 4: sum(BOQ leaf) * (1+PPN) <= nilai kontrak ----
    try:
        from apps.boq.models import BOQItem  # type: ignore
        if 'boq' in locals() and boq is not None:
            from django.db.models import Sum
            agg = BOQItem.objects.filter(
                boq_revision=boq, is_leaf=True
            ).aggregate(total=Sum("total_price"))
            sum_leaf = agg["total"] or Decimal("0")
            est_post_ppn = sum_leaf * (Decimal("1") + contract.ppn_pct / Decimal("100"))
            tolerance = Decimal(settings.RASMARA["MONEY_TOLERANCE"])
            if est_post_ppn - tolerance > contract.original_value:
                checks.append(GateCheck(
                    code="VALUE_EXCEEDS",
                    label="Total BOQ × (1+PPN) tidak boleh melebihi nilai kontrak.",
                    ok=False,
                    detail=f"BOQ pre-PPN Rp {sum_leaf:,.2f} → post-PPN Rp {est_post_ppn:,.2f} "
                            f"vs nilai kontrak Rp {contract.original_value:,.2f}.",
                ))
            else:
                checks.append(GateCheck(
                    code="VALUE_OK",
                    label="Nilai BOQ konsisten dengan nilai kontrak.",
                    ok=True,
                    detail=f"BOQ post-PPN Rp {est_post_ppn:,.2f} ≤ nilai kontrak Rp {contract.original_value:,.2f}.",
                ))
    except (ImportError, LookupError):
        pass  # sudah ada gate failure dari cek #3

    return GateResult(ok=all(c.ok for c in checks), checks=checks)


# ---------- State machine ----------
def _check_godmode(contract: Contract) -> bool:
    return contract.is_godmode_active


@transaction.atomic
def transition(contract: Contract, to_status: str, *, user=None,
                bypass_gate: bool = False) -> Contract:
    """Eksekusi transisi state. Validasi: legal transition + gate (utk activate)."""
    cur = contract.status
    if to_status == cur:
        return contract

    godmode = _check_godmode(contract)
    legal = LEGAL_TRANSITIONS.get(cur, set())
    if to_status not in legal and not godmode:
        raise InvalidStateTransitionError(
            f"Tidak bisa pindah dari {cur} ke {to_status}.",
            code="INVALID_TRANSITION",
        )

    # Khusus aktivasi: cek gate (kecuali bypass via godmode)
    if to_status == ContractStatus.ACTIVE and not (bypass_gate or godmode):
        result = evaluate_activation_gates(contract)
        if not result.ok:
            raise DomainError(
                "Gate aktivasi belum lengkap. " +
                "; ".join(f"{c.label}" for c in result.failed),
                code="ACTIVATION_GATE_FAILED",
            )

    contract.status = to_status
    contract.updated_by = user
    contract.save(update_fields=["status", "updated_at", "updated_by"])
    return contract


# ---------- Helpers ----------
def recalc_duration(contract: Contract) -> int:
    """Hitung ulang duration_days dari start/end. Inklusif."""
    if contract.start_date and contract.end_date:
        days = (contract.end_date - contract.start_date).days + 1
        contract.duration_days = days
        return days
    return contract.duration_days or 0


def is_user_in_scope(user, contract_id) -> bool:
    """Cek apakah user boleh akses kontrak ini (Inv. assigned_contract_ids)."""
    if user is None or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if user.assigned_contract_ids is None:
        return True
    return str(contract_id) in {str(x) for x in user.assigned_contract_ids}


def filter_contracts_for_user(qs, user):
    """Filter queryset Contract berdasarkan scope user."""
    if not user or not user.is_authenticated:
        return qs.none()
    if user.is_superuser or user.assigned_contract_ids is None:
        return qs
    return qs.filter(pk__in=user.assigned_contract_ids)


@transaction.atomic
def set_godmode(contract: Contract, *, hours: int, reason: str, user) -> Contract:
    """Aktifkan god-mode (Inv. 14)."""
    if hours <= 0 or hours > 72:
        raise DomainError("Window godmode 1-72 jam.", code="INVALID_GODMODE_WINDOW")
    if not reason or len(reason.strip()) < 8:
        raise DomainError("Alasan godmode wajib ≥ 8 karakter.", code="GODMODE_REASON_REQUIRED")
    contract.unlock_until = timezone.now() + timedelta(hours=hours)
    contract.unlock_reason = reason.strip()
    contract.updated_by = user
    contract.save(update_fields=["unlock_until", "unlock_reason", "updated_at", "updated_by"])
    # Tandai middleware godmode_bypass utk audit log selanjutnya
    from apps.core.middleware import set_godmode as set_thread_godmode
    set_thread_godmode(True, reason=reason.strip())
    return contract


@transaction.atomic
def clear_godmode(contract: Contract, user) -> Contract:
    contract.unlock_until = None
    contract.unlock_reason = ""
    contract.updated_by = user
    contract.save(update_fields=["unlock_until", "unlock_reason", "updated_at", "updated_by"])
    return contract
