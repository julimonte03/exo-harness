"""Authentication (signed bearer tokens) and authorization (roles)."""

from .permissions import Role, allowed, require

__all__ = ["Role", "allowed", "require"]
