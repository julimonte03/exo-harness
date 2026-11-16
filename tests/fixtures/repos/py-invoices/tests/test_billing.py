from decimal import Decimal

import pytest

from invoices.billing import InvoiceStatus, LineItem, compute_totals, lookup_discount, transition
from invoices.billing.balance import balance_due
from invoices.billing.discounts import Discount
from invoices.core.errors import ConflictError, ValidationError
from invoices.payments.ledger import Payment, PaymentStatus


def test_rounding_discount_and_tax():
    assert LineItem("Support", 3, Decimal("33.335")).amount == Decimal("100.01")  # half up
    totals = compute_totals([LineItem("Plan", 2, Decimal("50"))], "US-CA", lookup_discount("welcome10"))
    assert (totals.discount, totals.tax, totals.total) == (Decimal("10"), Decimal("6.53"), Decimal("96.53"))
    lines = [LineItem("Consulting", 4, Decimal("120")), LineItem("Manual", 2, Decimal("15.50"), "reduced")]
    assert compute_totals(lines, "DE").tax == Decimal("93.37")  # 480.00 at 19% + 31.00 at 7%


def test_discounts_and_lines_have_limits():
    assert compute_totals([LineItem("Pen", 1, Decimal("30"))], "ES", lookup_discount("CREDIT50")).total == 0
    with pytest.raises(ValidationError):
        Discount("HALFPLUS", percent=Decimal("60"))
    with pytest.raises(ValidationError):
        compute_totals([LineItem("Item", 1, Decimal("1.00"))] * 201, "ES")
    with pytest.raises(ValidationError):
        LineItem("Nothing", 0, Decimal("1.00"))


@pytest.mark.parametrize(("current", "target"), [("draft", "paid"), ("paid", "void"), ("partially_paid", "void")])
def test_forbidden_transitions(current, target):
    with pytest.raises(ConflictError):
        transition(InvoiceStatus(current), InvoiceStatus(target))


def test_balance_counts_only_the_money_kept():
    settled = Payment(1, Decimal("60.00"), PaymentStatus.SETTLED)
    settled.refund(Decimal("10.00"))
    assert balance_due(Decimal("100.00"), [settled, Payment(1, Decimal("40.00"))]) == Decimal("50.00")
