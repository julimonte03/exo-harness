"""What a customer still owes on an invoice."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from ..payments.ledger import Payment, settled_amount


def balance_due(total: Decimal, payments: Iterable[Payment]) -> Decimal:
    """Total minus the money actually kept; never below zero."""
    return max(total - settled_amount(payments), Decimal("0.00"))
