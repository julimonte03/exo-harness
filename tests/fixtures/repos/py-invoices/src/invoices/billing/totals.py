"""Invoice totals: line amounts, discount, tax and grand total."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from ..core.errors import ValidationError
from .discounts import Discount, discount_amount
from .tax import tax_for

MAX_LINE_ITEMS = 200
MAX_QUANTITY = 10_000


def to_cents(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class LineItem:
    description: str
    quantity: int
    unit_price: Decimal
    tax_category: str = "standard"

    def __post_init__(self) -> None:
        if not 1 <= self.quantity <= MAX_QUANTITY:
            raise ValidationError(f"quantity must be between 1 and {MAX_QUANTITY}")
        if self.unit_price < 0:
            raise ValidationError("unit price cannot be negative")

    @property
    def amount(self) -> Decimal:
        return to_cents(self.unit_price * self.quantity)


@dataclass(frozen=True)
class Totals:
    subtotal: Decimal
    discount: Decimal
    tax: Decimal
    total: Decimal


def compute_totals(lines: list[LineItem], region: str, discount: Discount | None = None) -> Totals:
    """The discount is spread over the lines by amount; each line pays its own tax rate."""
    if not 1 <= len(lines) <= MAX_LINE_ITEMS:
        raise ValidationError(f"an invoice has between 1 and {MAX_LINE_ITEMS} lines")
    subtotal = sum((line.amount for line in lines), Decimal("0.00"))
    off = to_cents(discount_amount(subtotal, discount))
    tax = Decimal("0")
    for line in lines:
        share = line.amount / subtotal if subtotal else Decimal("0")
        tax += tax_for(line.amount - off * share, region, line.tax_category)
    tax = to_cents(tax)
    return Totals(subtotal, off, tax, subtotal - off + tax)
