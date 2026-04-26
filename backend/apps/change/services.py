"""Service VO + Addendum (Bagian 6 CLAUDE.md).

Inti: state machine VO, sign flow Addendum, clone revisi BOQ + apply VO items.
"""
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from common.exceptions import DomainError, InvalidStateTransitionError

from .models import (
    Addendum,
    AddendumStatus,
    AddendumType,
    AddendumVO,
    VariationOrder,
    VOItem,
    VOItemAction,
    VOStatus,
)


# ====================== VO state machine (Bagian 6.1, Inv. 6) ======================
LEGAL_VO_TRANSITIONS: dict[str, set[str]] = {
    VOStatus.DRAFT: {VOStatus.UNDER_REVIEW, VOStatus.REJECTED},
    VOStatus.UNDER_REVIEW: {VOStatus.APPROVED, VOStatus.REJECTED, VOStatus.DRAFT},
    VOStatus.APPROVED: {VOStatus.BUNDLED, VOStatus.REJECTED},
    VOStatus.REJECTED: set(),  # terminal
    VOStatus.BUNDLED: set(),  # terminal
}


def _assert_vo_writable(vo: VariationOrder) -> None:
    """Edit (CRUD VOItem, edit fields VO) hanya saat status DRAFT."""
    if vo.status != VOStatus.DRAFT:
        raise DomainError(
            f"VO sudah {vo.get_status_display()}, tidak bisa diedit langsung.",
            code="VO_NOT_DRAFT",
        )


def _vo_transition(vo: VariationOrder, to_status: str, *, user=None) -> None:
    cur = vo.status
    if to_status == cur:
        return
    legal = LEGAL_VO_TRANSITIONS.get(cur, set())
    if to_status not in legal:
        raise InvalidStateTransitionError(
            f"VO transisi {cur} -> {to_status} tidak valid.",
            code="VO_INVALID_TRANSITION",
        )
    vo.status = to_status
    now = timezone.now()
    if to_status == VOStatus.UNDER_REVIEW:
        vo.submitted_at = now
        vo.submitted_by = user
    elif to_status == VOStatus.APPROVED:
        vo.approved_at = now
        vo.approved_by = user
    elif to_status == VOStatus.REJECTED:
        vo.rejected_at = now
        vo.rejected_by = user
    elif to_status == VOStatus.BUNDLED:
        # set saat di-bundle Addendum SIGNED — tidak ada timestamp khusus
        pass
    elif to_status == VOStatus.DRAFT:
        # return to draft (revert reviewing)
        vo.submitted_at = None
        vo.submitted_by = None
    vo.save()


@transaction.atomic
def vo_submit(vo: VariationOrder, *, user) -> VariationOrder:
    """DRAFT -> UNDER_REVIEW. Validasi: minimal punya 1 VOItem."""
    if not vo.items.exists():
        raise DomainError("VO harus punya minimal 1 item perubahan.",
                          code="VO_EMPTY")
    _vo_transition(vo, VOStatus.UNDER_REVIEW, user=user)
    return vo


@transaction.atomic
def vo_return_to_draft(vo: VariationOrder, *, user) -> VariationOrder:
    _vo_transition(vo, VOStatus.DRAFT, user=user)
    return vo


@transaction.atomic
def vo_approve(vo: VariationOrder, *, user) -> VariationOrder:
    _vo_transition(vo, VOStatus.APPROVED, user=user)
    return vo


@transaction.atomic
def vo_reject(vo: VariationOrder, *, user, reason: str = "") -> VariationOrder:
    vo.rejection_reason = reason
    _vo_transition(vo, VOStatus.REJECTED, user=user)
    return vo


# ====================== Addendum sign flow (Bagian 6.3) ======================
@transaction.atomic
def addendum_bundle_vo(addendum: Addendum, *, vo_ids: list, user) -> Addendum:
    """Tambah VO ke addendum DRAFT. Hanya VO APPROVED yang boleh.

    1 VO hanya boleh di-bundle ke 1 addendum (UniqueConstraint addvo_unique_vo_max1).
    """
    if addendum.status != AddendumStatus.DRAFT:
        raise DomainError("Addendum sudah SIGNED, tidak bisa ubah bundle VO.",
                          code="ADDENDUM_LOCKED")
    vos = list(VariationOrder.objects.filter(
        pk__in=vo_ids, contract=addendum.contract,
    ))
    if len(vos) != len(vo_ids):
        raise DomainError("Beberapa VO tidak ditemukan di kontrak ini.",
                          code="VO_NOT_FOUND")
    not_approved = [v for v in vos if v.status != VOStatus.APPROVED]
    if not_approved:
        raise DomainError(
            f"Hanya VO APPROVED yang boleh di-bundle. Belum APPROVED: "
            f"{', '.join(v.number for v in not_approved)}.",
            code="VO_NOT_APPROVED",
        )
    for vo in vos:
        # cek unique: VO belum di-bundle ke addendum lain
        existing = AddendumVO.objects.filter(vo=vo).first()
        if existing and existing.addendum_id != addendum.id:
            raise DomainError(
                f"VO {vo.number} sudah di-bundle ke addendum {existing.addendum.number}.",
                code="VO_ALREADY_BUNDLED",
            )
        AddendumVO.objects.get_or_create(addendum=addendum, vo=vo)
    return addendum


@transaction.atomic
def addendum_unbundle_vo(addendum: Addendum, *, vo_ids: list, user) -> Addendum:
    if addendum.status != AddendumStatus.DRAFT:
        raise DomainError("Addendum sudah SIGNED, tidak bisa ubah bundle VO.",
                          code="ADDENDUM_LOCKED")
    AddendumVO.objects.filter(addendum=addendum, vo_id__in=vo_ids).delete()
    return addendum


def _check_kpa_threshold(addendum: Addendum) -> bool:
    """Inv. 7: kalau |value_delta| > 10% nilai original, butuh kpa_approval."""
    if addendum.value_delta == 0:
        return True
    contract = addendum.contract
    threshold_pct = Decimal(str(settings.RASMARA["KPA_THRESHOLD_PCT"]))
    threshold = contract.original_value * threshold_pct / Decimal("100")
    if abs(addendum.value_delta) > threshold:
        if not addendum.kpa_approval:
            return False
    return True


@transaction.atomic
def addendum_sign(addendum: Addendum, *, user) -> Addendum:
    """SIGN addendum: legal action. Trigger:
      1. Bundle VO APPROVED → BUNDLED
      2. Clone revisi BOQ aktif → revisi baru DRAFT (kalau ada VO BOQ-affecting)
      3. Apply VO items ke revisi baru
      4. Approve & aktifkan revisi baru, lama → SUPERSEDED
      5. Update contract: current_value, end_date, duration_days
    """
    if addendum.status != AddendumStatus.DRAFT:
        raise DomainError("Addendum tidak dalam status DRAFT.",
                          code="ADDENDUM_NOT_DRAFT")

    # KPA threshold cek (Inv. 7)
    if not _check_kpa_threshold(addendum):
        contract = addendum.contract
        threshold_pct = settings.RASMARA["KPA_THRESHOLD_PCT"]
        raise DomainError(
            f"|value_delta| Rp {abs(addendum.value_delta):,.2f} melebihi "
            f"{threshold_pct}% nilai original (Rp {contract.original_value:,.2f}). "
            "Wajib upload kpa_approval terlebih dahulu.",
            code="KPA_REQUIRED",
        )

    # Bundle VO → BUNDLED
    vos = list(addendum.vos.all())
    for vo in vos:
        if vo.status != VOStatus.APPROVED:
            raise DomainError(
                f"VO {vo.number} bukan APPROVED ({vo.status}). "
                "Lepas atau approve dulu.",
                code="VO_NOT_APPROVED",
            )

    # Hitung apakah ada VO BOQ-affecting (any VOItem != non-boq)
    has_boq_changes = False
    for vo in vos:
        if vo.items.exists():
            has_boq_changes = True
            break

    # Clone revisi BOQ kalau perlu
    new_revision = None
    if has_boq_changes:
        new_revision = _spawn_boq_revision_from_addendum(addendum, vos, user=user)

    # Update VO status -> BUNDLED
    for vo in vos:
        _vo_transition(vo, VOStatus.BUNDLED, user=user)

    # Update contract
    contract = addendum.contract
    if addendum.addendum_type in (AddendumType.VALUE_CHANGE, AddendumType.COMBINED, AddendumType.CCO):
        contract.current_value = (contract.current_value + addendum.value_delta).quantize(Decimal("0.01"))
    if addendum.addendum_type in (AddendumType.EXTENSION, AddendumType.COMBINED):
        if addendum.new_end_date:
            contract.end_date = addendum.new_end_date
        elif addendum.days_delta:
            from datetime import timedelta
            contract.end_date = contract.end_date + timedelta(days=addendum.days_delta)
        # duration_days otomatis di-recompute di Contract.save()
    contract.updated_by = user
    contract.save()

    # Tandai addendum SIGNED
    addendum.status = AddendumStatus.SIGNED
    addendum.signed_at = timezone.now()
    addendum.signed_by = user
    addendum.save()

    return addendum


@transaction.atomic
def _spawn_boq_revision_from_addendum(addendum: Addendum, vos: list[VariationOrder], *, user):
    """Clone revisi BOQ aktif → revisi baru, apply VO items, approve & activate.

    Bagian 5.3 + 5.4 + 6.3 CLAUDE.md.
    """
    from apps.boq.models import BOQItem, BOQRevision, BOQRevisionStatus, ChangeType
    from apps.boq.services import recompute_all

    contract = addendum.contract
    old_rev = BOQRevision.objects.filter(
        contract=contract, is_active=True,
    ).first()
    if old_rev is None:
        raise DomainError("Tidak ada revisi BOQ aktif untuk di-clone.",
                          code="NO_ACTIVE_REVISION")

    # Versi baru
    max_v = (BOQRevision.objects.filter(contract=contract)
                                  .order_by("-version").values_list("version", flat=True).first())
    new_version = (max_v or 0) + 1

    # Old jadi SUPERSEDED dulu (sebelum kita buat new is_active=True, biar
    # partial unique constraint Inv.1 tidak bentrok)
    old_rev.is_active = False
    old_rev.status = BOQRevisionStatus.SUPERSEDED
    old_rev.save(update_fields=["is_active", "status", "updated_at"])

    new_rev = BOQRevision.objects.create(
        contract=contract,
        version=new_version,
        status=BOQRevisionStatus.DRAFT,
        is_active=False,  # set True setelah apply VO items
        addendum=addendum,
        notes=f"Spawn dari Addendum {addendum.number} (Bagian 5.3).",
    )

    # Clone semua items lama ke revisi baru, set source_item & change_type
    old_items = list(BOQItem.objects.filter(boq_revision=old_rev)
                                       .order_by("level", "display_order"))
    old_to_new = {}  # old_id -> new_item
    # Pass 1: create new items tanpa parent (set parent di pass 2 setelah semua dibuat)
    for o in old_items:
        n = BOQItem.objects.create(
            boq_revision=new_rev,
            facility=o.facility,
            code=o.code,
            description=o.description,
            unit=o.unit,
            volume=o.volume,
            unit_price=o.unit_price,
            total_price=o.total_price,
            weight_pct=o.weight_pct,
            level=o.level,
            display_order=o.display_order,
            is_leaf=o.is_leaf,
            source_item=o,
            change_type=ChangeType.UNCHANGED,
            planned_start_week=o.planned_start_week,
            planned_duration_weeks=o.planned_duration_weeks,
            notes=o.notes,
        )
        old_to_new[o.id] = n
    # Pass 2: set parent_id mapping ke new
    for o in old_items:
        if o.parent_id and o.parent_id in old_to_new:
            new_obj = old_to_new[o.id]
            new_obj.parent = old_to_new[o.parent_id]
            new_obj.save(update_fields=["parent", "updated_at"])

    # Apply VO items
    for vo in vos:
        for vi in vo.items.all().select_related("source_boq_item", "facility", "parent_boq_item"):
            _apply_vo_item(vi, new_rev, old_to_new)

    # Recompute everything
    recompute_all(new_rev)

    # Activate new
    new_rev.is_active = True
    new_rev.status = BOQRevisionStatus.APPROVED
    new_rev.approved_at = timezone.now()
    new_rev.approved_by = user
    new_rev.save()

    # Migrasi progres mingguan (Bagian 5.4) — akan diaktifkan saat Modul 6 (Pelaporan)
    # Sementara skip, akan ada at modul 6.

    return new_rev


def _apply_vo_item(vi, new_rev, old_to_new):
    """Terapkan satu VOItem ke revisi BOQ baru (yang sudah berisi clone).

    old_to_new: dict[old_item_id, new_item_obj]
    """
    from apps.boq.models import BOQItem, ChangeType

    action = vi.action
    if action == VOItemAction.ADD:
        # Item baru — di facility yang ditunjuk
        if not vi.facility_id:
            raise DomainError("VOItem ADD wajib punya facility.",
                              code="ADD_NEEDS_FACILITY")
        parent_new = None
        if vi.parent_boq_item_id and vi.parent_boq_item_id in old_to_new:
            parent_new = old_to_new[vi.parent_boq_item_id]
        BOQItem.objects.create(
            boq_revision=new_rev,
            facility=vi.facility,
            code=vi.code or "VO-NEW",
            description=vi.description,
            unit=vi.unit,
            volume=vi.volume_delta,
            unit_price=vi.unit_price,
            parent=parent_new,
            change_type=ChangeType.ADDED,
        )
    elif action == VOItemAction.INCREASE:
        if not vi.source_boq_item_id or vi.source_boq_item_id not in old_to_new:
            raise DomainError("VOItem INCREASE butuh source_boq_item valid.",
                              code="INCREASE_BAD_SOURCE")
        item = old_to_new[vi.source_boq_item_id]
        if vi.volume_delta <= 0:
            raise DomainError("INCREASE harus volume_delta > 0.", code="INCREASE_BAD_DELTA")
        item.volume = item.volume + vi.volume_delta
        item.change_type = ChangeType.MODIFIED
        item.save()
    elif action == VOItemAction.DECREASE:
        if not vi.source_boq_item_id or vi.source_boq_item_id not in old_to_new:
            raise DomainError("VOItem DECREASE butuh source_boq_item valid.",
                              code="DECREASE_BAD_SOURCE")
        item = old_to_new[vi.source_boq_item_id]
        if vi.volume_delta >= 0:
            raise DomainError("DECREASE harus volume_delta < 0.", code="DECREASE_BAD_DELTA")
        new_vol = item.volume + vi.volume_delta  # delta negatif
        if new_vol < 0:
            raise DomainError(
                f"Volume tidak boleh < 0. Item {item.full_code}: {item.volume} + {vi.volume_delta} = {new_vol}",
                code="VOLUME_NEGATIVE",
            )
        item.volume = new_vol
        item.change_type = ChangeType.MODIFIED
        item.save()
    elif action == VOItemAction.MODIFY_SPEC:
        if not vi.source_boq_item_id or vi.source_boq_item_id not in old_to_new:
            raise DomainError("VOItem MODIFY_SPEC butuh source_boq_item valid.",
                              code="MODIFY_BAD_SOURCE")
        item = old_to_new[vi.source_boq_item_id]
        # Snapshot old utk audit
        item.old_description = item.description
        item.old_unit = item.unit
        if vi.new_description:
            item.description = vi.new_description
        if vi.new_unit:
            item.unit = vi.new_unit
        if vi.unit_price > 0:
            item.unit_price = vi.unit_price
        item.change_type = ChangeType.MODIFIED
        item.save()
    elif action == VOItemAction.REMOVE:
        if not vi.source_boq_item_id or vi.source_boq_item_id not in old_to_new:
            raise DomainError("VOItem REMOVE butuh source_boq_item valid.",
                              code="REMOVE_BAD_SOURCE")
        item = old_to_new[vi.source_boq_item_id]
        # Tombstone (Bagian 6.2): change_type=REMOVED, tidak hard-delete
        item.change_type = ChangeType.REMOVED
        item.save(update_fields=["change_type", "updated_at"])
    elif action == VOItemAction.REMOVE_FACILITY:
        if not vi.facility_id:
            raise DomainError("VOItem REMOVE_FACILITY wajib punya facility.",
                              code="REMOVE_FAC_BAD")
        # Cascade tombstone semua item di fasilitas tersebut di revisi baru
        BOQItem.objects.filter(
            boq_revision=new_rev, facility_id=vi.facility_id,
        ).update(change_type=ChangeType.REMOVED)
    else:
        raise DomainError(f"VOItem action tidak dikenal: {action}",
                          code="UNKNOWN_VO_ACTION")
