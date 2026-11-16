import pytest

from invoices.auth import Role, allowed, require
from invoices.auth.tokens import MAX_TTL_SECONDS, issue_token, verify_token
from invoices.core.errors import AuthError, ConfigError, PermissionDenied

NOW = 1_780_000_000


@pytest.mark.parametrize("permission", ["invoices:void", "payments:refund", "customers:write"])
def test_only_admins_void_refund_and_edit_customers(permission):
    assert allowed(Role.ADMIN, permission) and not allowed(Role.ACCOUNTANT, permission)
    with pytest.raises(PermissionDenied):
        require(Role.VIEWER, "invoices:write")


def test_tokens_expire_and_resist_tampering(signing_key):
    issued = issue_token("ana@example.com", Role.ACCOUNTANT, ttl=60, now=NOW)
    assert verify_token(issued, now=NOW + 59).role is Role.ACCOUNTANT
    with pytest.raises(AuthError, match="expired"):
        verify_token(issued, now=NOW + 60)
    admin_body = issue_token("ana@example.com", Role.ADMIN, now=NOW).split(".")[0]
    with pytest.raises(AuthError, match="signature"):
        verify_token(admin_body + "." + issued.split(".")[1], now=NOW)
    with pytest.raises(AuthError):
        issue_token("ana@example.com", Role.VIEWER, ttl=MAX_TTL_SECONDS + 1)


@pytest.mark.parametrize(("key", "error"), [(None, "not set"), ("too-short", "at least 32")])
def test_the_signing_key_comes_from_the_environment(monkeypatch, key, error):
    monkeypatch.delenv("INVOICES_SIGNING_KEY", raising=False)
    if key:
        monkeypatch.setenv("INVOICES_SIGNING_KEY", key)
    with pytest.raises(ConfigError, match=error):
        issue_token("ana@example.com", Role.VIEWER)
