"""Sandbox token endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from invoices.auth import Role
from invoices.auth.tokens import issue_token
from invoices.core.config import Settings

from .deps import get_settings
from .schemas import TokenOut, TokenRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=TokenOut)
def create_token(body: TokenRequest, settings: Settings = Depends(get_settings)) -> TokenOut:
    """Issue a token for any role, without a password. Only the sandbox has this endpoint."""
    if not settings.sandbox:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    if body.role not in {role.value for role in Role}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"unknown role: {body.role}")
    return TokenOut(
        access_token=issue_token(body.subject, Role(body.role), body.ttl_seconds),
        expires_in=body.ttl_seconds,
    )
