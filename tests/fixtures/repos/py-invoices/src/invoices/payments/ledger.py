"""Payments recorded against invoices."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from ..core.errors import ValidationError


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SETTLED = "settled"
    REFUNDED = "refunded"


KEPT = (PaymentStatus.SETTLED, PaymentStatus.REFUNDED)


@dataclass
class Payment:
    invoice_id: int
    amount: Decimal
    status: PaymentStatus = PaymentStatus.PENDING
    refunded: Decimal = Decimal("0.00")

    def refund(self, amount: Decimal) -> None:
        if self.status not in KEPT or not 0 < amount <= self.amount - self.refunded:
            raise ValidationError("a refund is positive and at most what is left of the payment")
        self.refunded += amount
        if self.refunded == self.amount:
            self.status = PaymentStatus.REFUNDED


def settled_amount(payments: Iterable[Payment]) -> Decimal:
    """Money actually kept: settled payments minus their refunds. Database rows work too."""
    return sum((p.amount - p.refunded for p in payments if p.status in KEPT), Decimal("0.00"))
