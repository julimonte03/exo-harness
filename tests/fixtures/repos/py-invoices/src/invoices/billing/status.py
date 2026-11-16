"""Invoice lifecycle: the only transitions an invoice may go through."""

from __future__ import annotations

from enum import Enum

from ..core.errors import ConflictError


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    VOID = "void"


S = InvoiceStatus
# Paid and void are final. An invoice with money on it is refunded before it is voided.
ALLOWED = {
    S.DRAFT: {S.ISSUED, S.VOID},
    S.ISSUED: {S.PARTIALLY_PAID, S.PAID, S.VOID},
    S.PARTIALLY_PAID: {S.PAID},
    S.PAID: set(),
    S.VOID: set(),
}


def transition(current: InvoiceStatus, target: InvoiceStatus) -> InvoiceStatus:
    """Return `target` if the lifecycle allows the move, or raise."""
    if target not in ALLOWED[current]:
        raise ConflictError(f"cannot move an invoice from {current.value} to {target.value}")
    return target
