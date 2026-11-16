"""Reconciliation: move an invoice forward as its payments settle."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from invoices.billing.status import InvoiceStatus, transition

from ..core.errors import ConflictError
from .ledger import Payment, settled_amount

# Processors round differently: one cent over the total is accepted.
OVERPAYMENT_TOLERANCE = Decimal("0.01")


def reconcile(status: InvoiceStatus, total: Decimal, payments: Iterable[Payment]) -> InvoiceStatus:
    """Status the invoice moves to once `payments` are counted."""
    if status in (InvoiceStatus.DRAFT, InvoiceStatus.VOID):
        raise ConflictError(f"a {status.value} invoice cannot take payments")
    settled = settled_amount(payments)
    if settled > total + OVERPAYMENT_TOLERANCE:
        raise ConflictError("payments exceed the invoice total", settled=settled, total=total)
    if settled >= total:
        target = InvoiceStatus.PAID
    elif settled > 0:
        target = InvoiceStatus.PARTIALLY_PAID
    else:
        return status
    return status if status == target else transition(status, target)
