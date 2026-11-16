"""Shared fixtures. The signing key is a throwaway value that exists only for the test run."""

import pytest


@pytest.fixture
def signing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INVOICES_SIGNING_KEY", "k" * 40)
