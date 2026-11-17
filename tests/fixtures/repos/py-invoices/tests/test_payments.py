from decimal import Decimal

import pytest

from invoices.billing.status import InvoiceStatus
from invoices.core.errors import ConflictError, ValidationError
from invoices.payments.cards import luhn_ok, mask, validate_card
from invoices.payments.ledger import Payment, PaymentStatus
from invoices.payments.reconciliation import reconcile

ISSUED, TOTAL = InvoiceStatus.ISSUED, Decimal("100.00")


def settled(amount: str) -> Payment:
    return Payment(7, Decimal(amount), PaymentStatus.SETTLED)


@pytest.mark.parametrize("number", ["4111 1111 1111 1111", "4242-4242-4242-4242", "5555555555554444"])
def test_published_test_cards_pass_in_the_sandbox(number):
    assert mask(validate_card(number, sandbox=True)).endswith(number[-4:])


def test_luhn_and_the_sandbox_list_are_enforced():
    with pytest.raises(ValidationError, match="Luhn"):
        validate_card("4111 1111 1111 1112", sandbox=False)
    number = next(n for n in (f"4000000000000{i:03d}" for i in range(1000)) if luhn_ok(n))
    assert validate_card(number, sandbox=False) == number
    with pytest.raises(ValidationError, match="sandbox"):
        validate_card(number, sandbox=True)


def test_reconciliation_moves_the_invoice_forward():
    assert reconcile(ISSUED, TOTAL, [settled("40.00")]) is InvoiceStatus.PARTIALLY_PAID
    assert reconcile(ISSUED, TOTAL, [settled("40.00"), settled("60.00")]) is InvoiceStatus.PAID
    assert reconcile(ISSUED, TOTAL, [settled("100.01")]) is InvoiceStatus.PAID  # one cent over is fine
    with pytest.raises(ConflictError):
        reconcile(ISSUED, TOTAL, [settled("100.02")])
    with pytest.raises(ConflictError):
        reconcile(InvoiceStatus.DRAFT, TOTAL, [settled("10.00")])
    with pytest.raises(ValidationError):  # a refund cannot exceed the payment
        settled("25.00").refund(Decimal("25.01"))
