"""Customers and the checks every customer record passes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from ..core.errors import ValidationError

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$")
REGIONS = ("US-CA", "US-NY", "DE", "ES")


def within_credit_limit(limit: Decimal, outstanding: Decimal, amount: Decimal) -> bool:
    """A new invoice fits if what the customer already owes plus the invoice stays within it."""
    return outstanding + amount <= limit


@dataclass
class Customer:
    name: str
    email: str
    tax_region: str
    credit_limit: Decimal = Decimal("5000.00")
    id: int | None = None

    def __post_init__(self) -> None:
        self.email = self.email.strip().lower()
        if not _EMAIL.match(self.email):
            raise ValidationError(f"not an email address: {self.email!r}")
        if self.tax_region not in REGIONS:
            raise ValidationError(f"unsupported tax region: {self.tax_region}")
        if self.credit_limit < 0:
            raise ValidationError("the credit limit cannot be negative")
