from decimal import Decimal

import pytest

from invoices.core.errors import ConflictError, NotFoundError, ValidationError
from invoices.customers.directory import CustomerDirectory
from invoices.customers.models import Customer, within_credit_limit


def test_emails_are_normalized_and_unique():
    directory = CustomerDirectory()
    assert directory.add(Customer("Ada Example", " Ada@Example.com ", "DE")).email == "ada@example.com"
    with pytest.raises(ConflictError):
        directory.add(Customer("Ada Again", "ADA@example.com", "ES"))
    with pytest.raises(NotFoundError):
        directory.get(42)


def test_credit_limits():
    with pytest.raises(ValidationError):
        Customer("Bob Example", "bob@example.com", "ES", credit_limit=Decimal("-1"))
    assert within_credit_limit(Decimal("2000"), Decimal("1500"), Decimal("500.00"))
    assert not within_credit_limit(Decimal("2000"), Decimal("1500"), Decimal("500.01"))
