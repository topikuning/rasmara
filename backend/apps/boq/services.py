"""Service BOQ: hirarki, weights, leaf-flag, scope-lock, transitions."""
from decimal import Decimal
from typing import Iterable

from django.conf import settings
from django.db import transaction
from django.db.models import F, Q, Sum
from django.utils import timezone

from common.exceptions import DomainError, ScopeLockedError

from .models import BOQItem, BOQRevision, BOQRevisionStatus, ChangeType


# ---------- Scope lock ----------
def assert_revision_writable(revision: BOQRevision) -> None:
    """Cegah edit langsung saat revisi APPROVED & aktif (Inv. 2).

    Kecuali kontrak status DRAFT (V0 boleh edit langsung sebelum kontrak aktif - Inv. 3).
    """
    if revision.status == BOQRevisionStatus.SUPERSEDED:
        raise ScopeLockedError(
            f"Revisi V{revision.version} sudah SUPERSEDED — tidak bisa diedit.",
            code="REVISION_SUPERSEDED",
        )
    if revision.status == BOQRevisionStatus.APPROVED:
        # APPROVED: edit hanya boleh kalau kontrak masih DRAFT (V0 baseline) DAN kontrak status DRAFT.
        from apps.contract.models import ContractStatus
        if revision.contract.status != ContractStatus.DRAFT or revision.is_godmode_active():
            raise ScopeLockedError(
                "Revisi sudah APPROVED. Perubahan hanya melalui Addendum baru.",
                code="REVISION_LOCKED",
            )
    # Else: DRAFT -> bebas edit


def _is_godmode(rev: BOQRevision) -> bool:
    return bool(rev.contract.is_godmode_active)


# Patch utility ke BOQRevision
def _is_godmode_method(self):
    return self.contract.is_godmode_active


BOQRevision.is_godmode_active = _is_godmode_method


# ---------- Hirarki & full_code ----------
def recompute_full_codes(revision: BOQRevision) -> int:
    """Hitung ulang full_code semua item di revisi (path titik)."""
    items = list(BOQItem.objects.filter(boq_revision=revision)
                                  .only("id", "code", "parent_id"))
    by_id = {it.id: it for it in items}
    updated = 0
    for it in items:
        path = [it.code]
        node = it
        seen = set([it.id])
        while node.parent_id and node.parent_id not in seen:
            seen.add(node.parent_id)
            parent = by_id.get(node.parent_id)
            if not parent:
                break
            path.append(parent.code)
            node = parent
        new_code = ".".join(reversed(path))
        if new_code != it.full_code:
            BOQItem.objects.filter(pk=it.pk).update(full_code=new_code)
            updated += 1
    return updated


def recompute_levels(revision: BOQRevision) -> int:
    """Hitung level (kedalaman dari root) untuk semua item."""
    items = list(BOQItem.objects.filter(boq_revision=revision).only("id", "parent_id"))
    by_id = {it.id: it for it in items}
    updated = 0
    for it in items:
        depth = 0
        node = it
        seen = set([it.id])
        while node.parent_id and node.parent_id not in seen:
            seen.add(node.parent_id)
            parent = by_id.get(node.parent_id)
            if not parent:
                break
            depth += 1
            node = parent
        BOQItem.objects.filter(pk=it.pk).update(level=depth)
        updated += 1
    return updated


def recompute_leaf_flags(revision: BOQRevision) -> int:
    """is_leaf = True kalau tidak punya child di revisi yang sama."""
    # Reset semua jadi True
    BOQItem.objects.filter(boq_revision=revision).update(is_leaf=True)
    # Set parent jadi non-leaf
    parent_ids = (BOQItem.objects
                    .filter(boq_revision=revision, parent__isnull=False)
                    .values_list("parent_id", flat=True)
                    .distinct())
    n = BOQItem.objects.filter(pk__in=parent_ids).update(is_leaf=False)
    return n


def recompute_total_price(revision: BOQRevision) -> int:
    """total_price = volume * unit_price untuk leaf; sum children untuk parent.

    Computed bottom-up: leaf dulu, lalu parent ber-iterasi sampai stabil.
    """
    # Leaf: total = volume * unit_price
    BOQItem.objects.filter(boq_revision=revision, is_leaf=True).update(
        total_price=F("volume") * F("unit_price")
    )
    # Parent: sum children. Iterasi sampai tidak ada perubahan (max 5 level utk safety).
    for _ in range(8):
        # Untuk setiap parent: ambil sum total_price children
        parents = BOQItem.objects.filter(
            boq_revision=revision, is_leaf=False,
        ).values_list("id", flat=True)
        any_change = False
        for pid in parents:
            agg = BOQItem.objects.filter(
                boq_revision=revision, parent_id=pid,
            ).aggregate(total=Sum("total_price"))
            new_total = (agg["total"] or Decimal("0")).quantize(Decimal("0.01"))
            updated = BOQItem.objects.filter(pk=pid).exclude(
                total_price=new_total,
            ).update(total_price=new_total)
            if updated:
                any_change = True
        if not any_change:
            break
    return 1


def recompute_weight_pct(revision: BOQRevision) -> Decimal:
    """weight_pct per leaf = total_price / sum(seluruh leaf di revisi).

    Returns: total nilai leaf (PRE-PPN).
    """
    agg = BOQItem.objects.filter(
        boq_revision=revision, is_leaf=True,
    ).aggregate(total=Sum("total_price"))
    total = agg["total"] or Decimal("0")
    if total == 0:
        BOQItem.objects.filter(boq_revision=revision).update(weight_pct=Decimal("0"))
        return Decimal("0")
    # Set weight per item
    items = BOQItem.objects.filter(boq_revision=revision).only("id", "total_price", "is_leaf")
    for it in items:
        if not it.is_leaf:
            BOQItem.objects.filter(pk=it.pk).update(weight_pct=Decimal("0"))
            continue
        w = (it.total_price / total * Decimal("100")).quantize(Decimal("0.0001"))
        BOQItem.objects.filter(pk=it.pk).update(weight_pct=w)
    return total


@transaction.atomic
def recompute_all(revision: BOQRevision) -> dict:
    """One-shot: hitung level + full_code + leaf-flag + total + weight."""
    recompute_levels(revision)
    recompute_full_codes(revision)
    recompute_leaf_flags(revision)
    recompute_total_price(revision)
    total_leaf = recompute_weight_pct(revision)
    return {"total_leaf": total_leaf}


# ---------- Validate budget ----------
def validate_budget(revision: BOQRevision) -> dict:
    """Cek total BOQ * (1+PPN) <= nilai kontrak (Bagian 7, Inv. 4)."""
    contract = revision.contract
    agg = BOQItem.objects.filter(
        boq_revision=revision, is_leaf=True,
    ).aggregate(total=Sum("total_price"))
    sum_leaf = agg["total"] or Decimal("0")
    ppn_factor = Decimal("1") + contract.ppn_pct / Decimal("100")
    est_post_ppn = (sum_leaf * ppn_factor).quantize(Decimal("0.01"))
    tolerance = Decimal(settings.RASMARA["MONEY_TOLERANCE"])
    nilai_kontrak = contract.original_value
    gap = (nilai_kontrak - est_post_ppn).quantize(Decimal("0.01"))
    ok = est_post_ppn <= nilai_kontrak + tolerance
    return {
        "boq_pre_ppn": str(sum_leaf),
        "ppn_pct": str(contract.ppn_pct),
        "ppn_amount": str((sum_leaf * (contract.ppn_pct / Decimal("100"))).quantize(Decimal("0.01"))),
        "boq_post_ppn": str(est_post_ppn),
        "nilai_kontrak": str(nilai_kontrak),
        "gap": str(gap),
        "ok": ok,
        "tolerance": str(tolerance),
    }


# ---------- Approve ----------
@transaction.atomic
def approve_revision(revision: BOQRevision, *, user) -> BOQRevision:
    """Approve revisi BOQ. Validasi budget dulu (Inv. 4)."""
    if revision.status != BOQRevisionStatus.DRAFT:
        raise DomainError(
            f"Revisi sudah {revision.get_status_display()}, tidak bisa di-approve ulang.",
            code="ALREADY_APPROVED",
        )
    # Recompute dulu supaya total konsisten
    recompute_all(revision)
    # Cek budget
    budget = validate_budget(revision)
    if not budget["ok"]:
        raise DomainError(
            f"Total BOQ × (1+PPN) ({budget['boq_post_ppn']}) melebihi nilai kontrak "
            f"({budget['nilai_kontrak']}). Selisih Rp {budget['gap']}.",
            code="BUDGET_EXCEEDED",
        )
    revision.status = BOQRevisionStatus.APPROVED
    revision.is_active = True
    revision.approved_at = timezone.now()
    revision.approved_by = user
    revision.save(update_fields=["status", "is_active", "approved_at",
                                   "approved_by", "updated_at"])
    return revision


# ---------- Delete with parent_id-clear (Inv. 13) ----------
@transaction.atomic
def delete_item_safe(item: BOQItem) -> None:
    """Hapus BOQItem dengan clear parent_id child dulu (Inv. 13).

    Tanpa ini, child akan jadi orphan dengan parent_id menunjuk ke item terhapus.
    """
    # Set parent_id child ke parent dari item ini (promote child)
    new_parent_id = item.parent_id
    BOQItem.objects.filter(parent_id=item.pk).update(parent_id=new_parent_id)
    item.delete()
    # Recompute leaf-flag setelah delete
    recompute_leaf_flags(item.boq_revision)
    recompute_full_codes(item.boq_revision)
    recompute_levels(item.boq_revision)
    recompute_total_price(item.boq_revision)
    recompute_weight_pct(item.boq_revision)
