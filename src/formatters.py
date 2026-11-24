"""Format whole dollars and rates.

Meta's report amounts in this compilation are whole dollars. Display rounding
for rates and per-person figures is half-up, so the script and the write-up
use the same strings.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from src.constants import CATEGORY_LABELS


def _quantum(decimals: int) -> Decimal:
    return Decimal("1").scaleb(-decimals)


def usd(dollars: int) -> str:
    value = int(dollars)
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,}"


def usd_compact(dollars: int) -> str:
    """Short axis and bar label, half-up at the last shown digit."""
    value = Decimal(abs(int(dollars)))
    sign = "-" if int(dollars) < 0 else ""
    if value >= Decimal(1_000_000_000):
        shown = (value / Decimal(1_000_000_000)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return f"{sign}${shown}B"
    if value >= Decimal(1_000_000):
        shown = (value / Decimal(1_000_000)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        return f"{sign}${shown}M"
    if value >= Decimal(1_000):
        shown = (value / Decimal(1_000)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        return f"{sign}${shown}k"
    return f"{sign}${value}"


def millions(dollars: int) -> float:
    """Axis value in millions of dollars. Labels should use usd_compact."""
    return int(dollars) / 1_000_000


def rate_pct(numerator: int, denominator: int, decimals: int = 2) -> str:
    if int(denominator) == 0:
        return "n/a"
    value = (Decimal(int(numerator)) / Decimal(int(denominator))) * Decimal(100)
    rounded = value.quantize(_quantum(decimals), rounding=ROUND_HALF_UP)
    return f"{rounded}%"


def per_person(dollars: int, population: int) -> str:
    """Dollars per resident, half-up to the cent."""
    if int(population) == 0:
        return "n/a"
    value = Decimal(int(dollars)) / Decimal(int(population))
    rounded = value.quantize(_quantum(2), rounding=ROUND_HALF_UP)
    sign = "-" if rounded < 0 else ""
    return f"{sign}${abs(rounded):,.2f}"


def per_ad(dollars: int, ads: int) -> str:
    """Dollars per ad-listing, half-up to the cent."""
    if int(ads) == 0:
        return "n/a"
    value = Decimal(int(dollars)) / Decimal(int(ads))
    rounded = value.quantize(_quantum(2), rounding=ROUND_HALF_UP)
    sign = "-" if rounded < 0 else ""
    return f"{sign}${abs(rounded):,.2f}"


def pretty_category(code: object) -> str:
    return CATEGORY_LABELS.get(str(code), str(code))


def advertiser_label(page_name: str, disclaimer: str, limit: int = 42) -> str:
    """Page name, with the disclaimer when it identifies a different payer."""
    page = " ".join(str(page_name).split())
    disc = " ".join(str(disclaimer).split())
    if disc and disc != page and disc != "these ads ran without a disclaimer":
        label = f"{page} ({disc})"
    else:
        label = page
    if len(label) <= limit:
        return label
    return label[: limit - 1].rstrip() + "…"
