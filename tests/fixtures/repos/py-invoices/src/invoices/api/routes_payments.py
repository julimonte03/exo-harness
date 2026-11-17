"""Card payments and refunds."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from invoices.core.config import Settings
from invoices.payments.cards import validate_card
from invoices.payments.ledger import Payment, PaymentStatus
from invoices.payments.reconciliation import reconcile
from invoices.storage.models import PaymentRow

from .deps import get_invoices, get_payments, get_settings, requires
from .schemas import PaymentCreate, PaymentOut, RefundCreate

router = APIRouter(tags=["payments"])


@router.post("/invoices/{invoice_id}/payments", status_code=201, response_model=PaymentOut)
def pay_invoice(
    invoice_id: int,
    body: PaymentCreate,
    _=Depends(requires("payments:write")),
    invoices=Depends(get_invoices),
    payments=Depends(get_payments),
    settings: Settings = Depends(get_settings),
) -> PaymentOut:
    invoice = invoices.get(invoice_id)
    digits = validate_card(body.card_number, sandbox=settings.sandbox)
    # The sandbox gateway settles every accepted card at once.
    payment = Payment(invoice_id=invoice.id, amount=body.amount, status=PaymentStatus.SETTLED)
    invoice.status = reconcile(invoice.status, invoice.total, [*invoice.payments, payment])
    row = PaymentRow(
        invoice_id=invoice.id,
        amount=payment.amount,
        refunded=payment.refunded,
        status=payment.status.value,
        card_last4=digits[-4:],
    )
    return PaymentOut.model_validate(payments.add(row))


@router.post("/payments/{payment_id}/refund", response_model=PaymentOut)
def refund_payment(
    payment_id: int,
    body: RefundCreate,
    _=Depends(requires("payments:refund")),
    payments=Depends(get_payments),
) -> PaymentOut:
    row = payments.get(payment_id)
    payment = Payment(row.invoice_id, row.amount, PaymentStatus(row.status), row.refunded)
    payment.refund(body.amount)
    # The invoice status is left alone: accounting reopens it with a credit note.
    row.refunded, row.status = payment.refunded, payment.status.value
    return PaymentOut.model_validate(row)
