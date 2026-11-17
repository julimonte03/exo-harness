"""Invoice endpoints: create, read, list, issue and void."""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, status

from invoices.billing import InvoiceStatus, LineItem, compute_totals, lookup_discount, transition
from invoices.billing.balance import balance_due
from invoices.core.config import Settings
from invoices.core.errors import ConflictError
from invoices.customers.models import within_credit_limit
from invoices.storage.models import InvoiceRow

from .deps import get_customers, get_invoices, get_settings, requires
from .schemas import InvoiceCreate, InvoiceOut

router = APIRouter(prefix="/invoices", tags=["invoices"])
MAX_PAGE_SIZE = 100


def to_out(row: InvoiceRow) -> InvoiceOut:
    fields = {name: getattr(row, name) for name in InvoiceOut.model_fields if name != "balance_due"}
    return InvoiceOut(**fields, balance_due=balance_due(row.total, row.payments))


@router.post("", status_code=status.HTTP_201_CREATED, response_model=InvoiceOut)
def create_invoice(
    body: InvoiceCreate,
    _=Depends(requires("invoices:write")),
    invoices=Depends(get_invoices),
    customers=Depends(get_customers),
    settings: Settings = Depends(get_settings),
) -> InvoiceOut:
    customer = customers.get(body.customer_id)
    lines = [LineItem(**line.model_dump()) for line in body.lines]
    totals = compute_totals(lines, customer.tax_region, lookup_discount(body.discount_code))
    row = InvoiceRow(
        number=invoices.next_number(datetime.now(timezone.utc).year),
        customer_id=customer.id,
        status=InvoiceStatus.DRAFT,
        currency=settings.currency,
        lines=[line.model_dump(mode="json") for line in body.lines],
        **dataclasses.asdict(totals),
    )
    return to_out(invoices.add(row))


@router.get("", response_model=list[InvoiceOut])
def list_invoices(
    status_filter: InvoiceStatus | None = Query(default=None, alias="status"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=MAX_PAGE_SIZE),
    _=Depends(requires("invoices:read")),
    invoices=Depends(get_invoices),
) -> list[InvoiceOut]:
    return [to_out(row) for row in invoices.list(status_filter, offset, limit)]


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: int, _=Depends(requires("invoices:read")), invoices=Depends(get_invoices)
) -> InvoiceOut:
    return to_out(invoices.get(invoice_id))


@router.post("/{invoice_id}/issue", response_model=InvoiceOut)
def issue_invoice(
    invoice_id: int,
    _=Depends(requires("invoices:issue")),
    invoices=Depends(get_invoices),
    customers=Depends(get_customers),
) -> InvoiceOut:
    row = invoices.get(invoice_id)
    customer = customers.get(row.customer_id)
    outstanding = invoices.outstanding_for(customer.id)
    if not within_credit_limit(customer.credit_limit, outstanding, row.total):
        raise ConflictError("the invoice would exceed the customer's credit limit")
    row.status = transition(row.status, InvoiceStatus.ISSUED)
    row.issued_at = datetime.now(timezone.utc)
    return to_out(row)


@router.post("/{invoice_id}/void", response_model=InvoiceOut)
def void_invoice(
    invoice_id: int, _=Depends(requires("invoices:void")), invoices=Depends(get_invoices)
) -> InvoiceOut:
    row = invoices.get(invoice_id)
    if balance_due(row.total, row.payments) < row.total:
        raise ConflictError("refund the payments before voiding the invoice")
    row.status = transition(row.status, InvoiceStatus.VOID)
    return to_out(row)
