"""Roles and what each one may do."""

from __future__ import annotations

from enum import Enum

from ..core.errors import PermissionDenied


class Role(str, Enum):
    VIEWER = "viewer"
    ACCOUNTANT = "accountant"
    ADMIN = "admin"


READ = {"invoices:read", "customers:read", "payments:read"}
WRITE = {"invoices:write", "invoices:issue", "payments:write"}
# Voiding, refunding and editing customers move money or identities: admins only.
SENSITIVE = {"invoices:void", "payments:refund", "customers:write"}
GRANTS = {Role.VIEWER: READ, Role.ACCOUNTANT: READ | WRITE, Role.ADMIN: READ | WRITE | SENSITIVE}


def allowed(role: Role, permission: str) -> bool:
    return permission in GRANTS[role]


def require(role: Role, permission: str) -> None:
    if not allowed(role, permission):
        raise PermissionDenied(f"role {role.value} lacks {permission}")
