"""Translate domain errors into JSON responses."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..core import errors as domain

STATUS_BY_ERROR = (
    (domain.ValidationError, 422),
    (domain.NotFoundError, 404),
    (domain.ConflictError, 409),
    (domain.AuthError, 401),
    (domain.PermissionDenied, 403),
    (domain.ConfigError, 500),
)


def status_for(error: domain.InvoiceError) -> int:
    return next((code for kind, code in STATUS_BY_ERROR if isinstance(error, kind)), 400)


async def handle_domain_error(request: Request, error: domain.InvoiceError) -> JSONResponse:
    body: dict[str, object] = {"error": error.code, "message": error.message}
    if error.details:
        body["details"] = {key: str(value) for key, value in error.details.items()}
    return JSONResponse(status_code=status_for(error), content=body)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(domain.InvoiceError, handle_domain_error)
