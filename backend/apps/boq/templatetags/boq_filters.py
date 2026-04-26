"""Template filter format Rupiah & angka untuk PDF (Bagian 14.1)."""
from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


def _to_dec(v) -> Decimal:
    if v is None or v == "":
        return Decimal("0")
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _format_id(n: Decimal, decimals: int = 2) -> str:
    """1.234.567,89 (titik = ribuan, koma = desimal)."""
    sign = "-" if n < 0 else ""
    n = abs(n)
    quant = Decimal("1") if decimals == 0 else Decimal("0." + "0" * decimals)
    n = n.quantize(quant)
    s = f"{n:,.{decimals}f}"
    # default: 1,234,567.89 -> swap to 1.234.567,89
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return sign + s


@register.filter(name="fmt_money")
def fmt_money(value):
    return "Rp " + _format_id(_to_dec(value), 2)


@register.filter(name="fmt_num")
def fmt_num(value, decimals=0):
    try:
        decimals = int(decimals)
    except (TypeError, ValueError):
        decimals = 0
    return _format_id(_to_dec(value), decimals)
