"""SQLAlchemy tables. Money is NUMERIC, never float; rows mirror the domain dataclasses."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from invoices.billing.status import InvoiceStatus


class Base(DeclarativeBase):
    type_annotation_map = {Decimal: sa.Numeric(12, 2), list: sa.JSON}


class CustomerRow(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(200))
    email: Mapped[str] = mapped_column(sa.String(254), unique=True)
    tax_region: Mapped[str] = mapped_column(sa.String(8))
    credit_limit: Mapped[Decimal]


class InvoiceRow(Base):
    __tablename__ = "invoices"
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(sa.String(32), unique=True)
    customer_id: Mapped[int] = mapped_column(sa.ForeignKey("customers.id"))
    status: Mapped[InvoiceStatus] = mapped_column(
        sa.Enum(InvoiceStatus, native_enum=False, values_callable=lambda e: [m.value for m in e]),
        index=True,
    )
    currency: Mapped[str] = mapped_column(sa.String(3))
    lines: Mapped[list]
    subtotal: Mapped[Decimal]
    discount: Mapped[Decimal]
    tax: Mapped[Decimal]
    total: Mapped[Decimal]
    issued_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    payments: Mapped[list[PaymentRow]] = relationship(lazy="selectin")


class PaymentRow(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(sa.ForeignKey("invoices.id"))
    amount: Mapped[Decimal]
    refunded: Mapped[Decimal] = mapped_column(default=Decimal("0.00"))
    status: Mapped[str] = mapped_column(sa.String(16))
    card_last4: Mapped[str] = mapped_column(sa.String(4))
