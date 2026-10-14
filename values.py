"""Shared money and local Excel date conversions, without application imports."""

from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

EPOCH = datetime(1899, 12, 30)


def dec(x: object) -> Decimal | None:
    if x in (None, ""):
        return None
    try:
        n = Decimal(str(x))
        return n if n.is_finite() else None
    except InvalidOperation:
        return None


def money(x: object) -> Decimal | None:
    n = dec(x)
    if n is None:
        return None
    try:
        return n.quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return None


def dt(x: object) -> datetime | None:
    if x in (None, ""):
        return None
    try:
        if isinstance(x, (int, float)):
            return EPOCH + timedelta(days=x)
        # Excel dates are local wall-clock values; discard XML date timezone markers.
        return datetime.fromisoformat(str(x)).replace(tzinfo=None)
    except (ValueError, OverflowError, TypeError):
        return None
