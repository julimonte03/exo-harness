"""Discount codes. A discount never takes a subtotal below zero."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ..core.errors import ValidationError

MAX_PERCENT = Decimal("50")


@dataclass(frozen=True)
class Discount:
    code: str
    percent: Decimal = Decimal("0")
    fixed: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if not 0 <= self.percent <= MAX_PERCENT:
            raise ValidationError(f"percentage discounts are capped at {MAX_PERCENT}%")


CATALOG = {
    "WELCOME10": Discount("WELCOME10", percent=Decimal("10")),
    "LOYAL25": Discount("LOYAL25", percent=Decimal("25")),
    "CREDIT50": Discount("CREDIT50", fixed=Decimal("50.00")),
}


def lookup(code: str | None) -> Discount | None:
    if code and code.strip().upper() not in CATALOG:
        raise ValidationError(f"unknown discount code: {code}")
    return CATALOG[code.strip().upper()] if code else None


def discount_amount(subtotal: Decimal, discount: Discount | None) -> Decimal:
    if discount is None:
        return Decimal("0.00")
    amount = subtotal * discount.percent / 100 if discount.percent else discount.fixed
    return min(amount, subtotal)
