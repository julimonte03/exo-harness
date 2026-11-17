"""Signed bearer tokens (HMAC-SHA256). The key comes from the environment, never from code."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass

from ..core.errors import AuthError, ConfigError
from .permissions import Role

MIN_KEY_LENGTH = 32
MAX_TTL_SECONDS = 12 * 3600


@dataclass(frozen=True)
class Principal:
    subject: str
    role: Role
    expires_at: int


def _sign(body: str) -> str:
    try:
        key = os.environ["INVOICES_SIGNING_KEY"]
    except KeyError:
        raise ConfigError("INVOICES_SIGNING_KEY is not set") from None
    if len(key) < MIN_KEY_LENGTH:
        raise ConfigError(f"INVOICES_SIGNING_KEY needs at least {MIN_KEY_LENGTH} characters")
    digest = hmac.new(key.encode(), body.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode()


def issue_token(subject: str, role: Role, ttl: int = 3600, now: float | None = None) -> str:
    if not 0 < ttl <= MAX_TTL_SECONDS:
        raise AuthError(f"a token lives between 1 and {MAX_TTL_SECONDS} seconds")
    claims = {"sub": subject, "role": role.value, "exp": int(now or time.time()) + ttl}
    body = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode()
    return f"{body}.{_sign(body)}"


def verify_token(token: str, now: float | None = None) -> Principal:
    body, _, signature = token.partition(".")
    if not signature or not hmac.compare_digest(signature, _sign(body)):
        raise AuthError("invalid token signature")
    claims = json.loads(base64.urlsafe_b64decode(body))
    if claims["exp"] <= int(now or time.time()):
        raise AuthError("token expired")
    return Principal(claims["sub"], Role(claims["role"]), claims["exp"])
