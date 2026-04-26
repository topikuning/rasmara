"""PDF export BOQ via WeasyPrint (Bagian 14.3)."""
from datetime import datetime
from decimal import Decimal

from django.db.models import Sum
from django.template.loader import render_to_string

from ..models import BOQItem, BOQRevision


def export_revision_pdf(revision: BOQRevision) -> bytes:
    contract = revision.contract
    items = list(
        BOQItem.objects.filter(boq_revision=revision)
                          .select_related("facility")
                          .order_by("facility__display_order", "facility__code",
                                      "display_order", "full_code")
    )
    total_leaf = (
        BOQItem.objects.filter(boq_revision=revision, is_leaf=True)
                          .aggregate(t=Sum("total_price"))["t"] or Decimal("0")
    )
    ppn_amount = (total_leaf * contract.ppn_pct / Decimal("100")).quantize(Decimal("0.01"))
    total_post = total_leaf + ppn_amount

    # Format tanggal Indonesia
    months_id = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
                 "Juli", "Agustus", "September", "Oktober", "November", "Desember"]

    def _fmt_id_date(d) -> str:
        if not d:
            return "-"
        return f"{d.day} {months_id[d.month]} {d.year}"

    ctx = {
        "contract": contract,
        "revision": revision,
        "items": items,
        "ppk_name": contract.ppk.full_name if contract.ppk_id else "-",
        "ppk_nip": contract.ppk.nip if contract.ppk_id else "-",
        "contractor_name": contract.contractor.name if contract.contractor_id else "-",
        "start_date": _fmt_id_date(contract.start_date),
        "end_date": _fmt_id_date(contract.end_date),
        "ppn_pct": str(contract.ppn_pct),
        "total_pre_ppn": str(total_leaf),
        "ppn_amount": str(ppn_amount),
        "total_post_ppn": str(total_post),
        "printed_at": datetime.now().strftime("%d-%m-%Y %H:%M"),
    }

    html = render_to_string("boq_pdf/revision.html", ctx)

    # Lazy import WeasyPrint (heavy)
    from weasyprint import HTML
    return HTML(string=html).write_pdf()
