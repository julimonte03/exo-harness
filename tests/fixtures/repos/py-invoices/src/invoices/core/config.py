"""Runtime settings, read once from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from .errors import ConfigError


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///./invoices.db"
    currency: str = "USD"
    sandbox: bool = True

    def __post_init__(self) -> None:
        if self.currency not in ("USD", "EUR", "GBP"):
            raise ConfigError(f"unsupported currency: {self.currency}")


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    return Settings(
        database_url=os.environ.get("INVOICES_DATABASE_URL", Settings.database_url),
        currency=os.environ.get("INVOICES_CURRENCY", "USD").upper(),
        sandbox=os.environ.get("INVOICES_SANDBOX", "true").lower() in {"1", "true", "yes"},
    )
