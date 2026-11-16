"""FastAPI dependencies: settings, database sessions and the caller's identity."""

from __future__ import annotations

from collections.abc import Callable, Iterator

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

import invoices.storage.repositories as repos
from invoices.auth.permissions import require
from invoices.auth.tokens import Principal, verify_token
from invoices.core.config import Settings
from invoices.core.errors import AuthError, PermissionDenied
from invoices.customers.directory import CustomerDirectory


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_session(request: Request) -> Iterator[Session]:
    with repos.session_scope(request.app.state.session_factory) as session:
        yield session


def get_invoices(session: Session = Depends(get_session)) -> repos.InvoiceRepository:
    return repos.InvoiceRepository(session)


def get_payments(session: Session = Depends(get_session)) -> repos.PaymentRepository:
    return repos.PaymentRepository(session)


def get_customers(session: Session = Depends(get_session)) -> CustomerDirectory:
    return CustomerDirectory.from_session(session)


def current_principal(authorization: str | None = Header(default=None)) -> Principal:
    scheme, _, credentials = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    try:
        return verify_token(credentials)
    except AuthError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, exc.message) from exc


def requires(permission: str) -> Callable[..., Principal]:
    """Dependency that lets a request through only if the caller's role grants `permission`."""

    def check(principal: Principal = Depends(current_principal)) -> Principal:
        try:
            require(principal.role, permission)
        except PermissionDenied as exc:
            raise HTTPException(status.HTTP_403_FORBIDDEN, exc.message) from exc
        return principal

    return check
