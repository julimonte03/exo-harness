"""Customer endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from invoices.customers.models import Customer

from .deps import get_customers, requires
from .schemas import CustomerCreate, CustomerOut

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CustomerOut)
def create_customer(
    body: CustomerCreate,
    _=Depends(requires("customers:write")),
    customers=Depends(get_customers),
) -> CustomerOut:
    created = customers.add(Customer(**body.model_dump()))
    return CustomerOut.model_validate(created)


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(
    customer_id: int, _=Depends(requires("customers:read")), customers=Depends(get_customers)
) -> CustomerOut:
    return CustomerOut.model_validate(customers.get(customer_id))
