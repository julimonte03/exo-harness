"""Customer lookups, in memory or backed by the database. Emails are unique, in any case."""

from __future__ import annotations

from ..core.errors import ConflictError, NotFoundError
from .models import Customer

try:  # the SQL repository needs SQLAlchemy; the CLI and the unit tests do without it
    from ..storage.repositories import CustomerRepository
except ImportError:
    CustomerRepository = None


class CustomerDirectory:
    def __init__(self, repository: CustomerRepository | None = None) -> None:
        self._repository = repository
        self._memory: dict[int, Customer] = {}

    @classmethod
    def from_session(cls, session: object) -> CustomerDirectory:
        if CustomerRepository is None:
            raise RuntimeError("install SQLAlchemy to keep customers in a database")
        return cls(CustomerRepository(session))

    def add(self, customer: Customer) -> Customer:
        if self.find_by_email(customer.email) is not None:
            raise ConflictError(f"a customer with email {customer.email} already exists")
        if self._repository is not None:
            return self._repository.add_customer(customer)
        customer.id = len(self._memory) + 1
        self._memory[customer.id] = customer
        return customer

    def get(self, customer_id: int) -> Customer:
        if self._repository is not None:
            return self._repository.get(customer_id)
        if customer_id not in self._memory:
            raise NotFoundError(f"customer {customer_id} not found")
        return self._memory[customer_id]

    def find_by_email(self, email: str) -> Customer | None:
        email = email.strip().lower()
        if self._repository is not None:
            return self._repository.find_by_email(email)
        return next((c for c in self._memory.values() if c.email == email), None)
