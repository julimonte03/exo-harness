"""Sessions and repositories: the only code that talks SQL."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from ..core.config import Settings
from ..core.errors import NotFoundError
from .models import CustomerRow, InvoiceRow, InvoiceStatus, PaymentRow


def make_session_factory(settings: Settings) -> sessionmaker[Session]:
    return sessionmaker(create_engine(settings.database_url), expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """One unit of work: commits if the block succeeds, rolls back if it raises."""
    with factory() as session, session.begin():
        yield session


class Repository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, row):
        self.session.add(row)
        self.session.flush()
        return row

    def get(self, row_id: int):
        row = self.session.get(self.model, row_id)
        if row is None:
            raise NotFoundError(f"{self.model.__tablename__} {row_id} not found")
        return row


class CustomerRepository(Repository):
    model = CustomerRow

    def add_customer(self, customer) -> CustomerRow:
        fields = ("name", "email", "tax_region", "credit_limit")
        return self.add(CustomerRow(**{name: getattr(customer, name) for name in fields}))

    def find_by_email(self, email: str) -> CustomerRow | None:
        return self.session.scalar(select(CustomerRow).where(CustomerRow.email == email))


class InvoiceRepository(Repository):
    model = InvoiceRow

    def next_number(self, year: int) -> str:
        prefix = f"INV-{year}-"
        query = select(func.count()).where(InvoiceRow.number.startswith(prefix))
        return f"{prefix}{self.session.scalar(query) + 1:06d}"

    def list(self, status: InvoiceStatus | None, offset: int, limit: int) -> list[InvoiceRow]:
        query = select(InvoiceRow).order_by(InvoiceRow.id).offset(offset).limit(limit)
        if status is not None:
            query = query.where(InvoiceRow.status == status)
        return list(self.session.scalars(query))

    def outstanding_for(self, customer_id: int) -> Decimal:
        """Totals of the customer's open invoices, before payments."""
        open_ = InvoiceRow.status.in_((InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID))
        owed = select(func.coalesce(func.sum(InvoiceRow.total), 0)).where(open_)
        return Decimal(self.session.scalar(owed.where(InvoiceRow.customer_id == customer_id)))


class PaymentRepository(Repository):
    model = PaymentRow
