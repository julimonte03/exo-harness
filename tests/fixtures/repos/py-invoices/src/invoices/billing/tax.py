"""Sales tax by region and product category."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from ..core import errors

if TYPE_CHECKING:  # annotations only
    from ..customers.models import Customer

CATEGORIES = ("standard", "reduced", "exempt")
# Rates of the sample deployment, in percent: (standard, reduced). Exempt goods pay nothing.
RATES = {
    "US-CA": (Decimal("7.25"), Decimal("0")),
    "US-NY": (Decimal("4.00"), Decimal("0")),
    "DE": (Decimal("19"), Decimal("7")),
    "ES": (Decimal("21"), Decimal("10")),
}


def tax_for(amount: Decimal, region: str, category: str = "standard") -> Decimal:
    """Tax on `amount`, unrounded: totals round once, at the end."""
    if region not in RATES or category not in CATEGORIES:
        raise errors.ValidationError(f"no tax rate for {category} goods in {region}")
    if category == "exempt":
        return Decimal("0")
    standard, reduced = RATES[region]
    return amount * (standard if category == "standard" else reduced) / 100


def region_of(customer: Customer) -> str:
    return customer.tax_region
