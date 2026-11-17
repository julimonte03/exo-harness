"""Request and response bodies."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from invoices.billing import InvoiceStatus
from invoices.billing.totals import MAX_LINE_ITEMS, MAX_QUANTITY


class LineItemIn(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    quantity: int = Field(ge=1, le=MAX_QUANTITY)
    unit_price: Decimal = Field(ge=0, max_digits=12, decimal_places=4)
    tax_category: Literal["standard", "reduced", "exempt"] = "standard"


class InvoiceCreate(BaseModel):
    customer_id: int
    lines: list[LineItemIn] = Field(min_length=1, max_length=MAX_LINE_ITEMS)
    discount_code: str | None = None


class InvoiceOut(BaseModel):
    id: int
    number: str
    customer_id: int
    status: InvoiceStatus
    currency: str
    lines: list[LineItemIn]
    subtotal: Decimal
    discount: Decimal
    tax: Decimal
    total: Decimal
    balance_due: Decimal
    issued_at: datetime | None = None


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(max_length=254)
    tax_region: str
    credit_limit: Decimal = Field(default=Decimal("5000.00"), ge=0)


class CustomerOut(CustomerCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    card_number: str = Field(min_length=13, max_length=23)


class RefundCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int
    amount: Decimal
    refunded: Decimal
    status: str
    card_last4: str


class TokenRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=254)
    role: str = "viewer"
    ttl_seconds: int = Field(default=3600, ge=1, le=43_200)


class TokenOut(BaseModel):
    access_token: str
    expires_in: int
