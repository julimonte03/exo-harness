"""core/secrets: escáner mínimo de secretos (base del guard S1 de F3).

Los tokens de prueba se arman por concatenación para que el código fuente no
contenga nada que parezca un secreto real.
"""

from __future__ import annotations

import pytest

from exo.core import secrets

AWS = "AKIA" + "Q" * 16
GITHUB = "gh" + "p_" + "a1B2" * 9
PRIVATE = "-----BEGIN " + "RSA PRIVATE KEY-----"
SLACK = "xo" + "xb-" + "123456789012-abcdefgh"


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        (f"clave: {AWS}", "aws-access-key"),
        (f"token {GITHUB} usado", "github-token"),
        (PRIVATE, "private-key"),
        (f"SLACK={SLACK}", "slack-token"),
        ('password = "s3cr3t-valor-largo"', "credential-assignment"),
        ("api_key: 'abcd1234efgh5678'", "credential-assignment"),
        ('TOKEN="zzzzzzzzzzzz"', "credential-assignment"),
    ],
)
def test_detecta(text: str, kind: str) -> None:
    findings = secrets.scan_text(f"linea 1\n{text}\n")
    assert [(f.line, f.kind) for f in findings] == [(2, kind)]
    assert "…" in findings[0].excerpt or len(findings[0].excerpt) <= 12


@pytest.mark.parametrize(
    "text",
    [
        'password = "<tu-password>"',
        'token = "${GITHUB_TOKEN}"',
        'secret = "xxxxxxxxxxxx"',
        'api_key = "********"',
        'password = "changeme"',
        'password = "corta"',
        "la palabra password sola",
        "AKIA corto",
    ],
)
def test_ignora_placeholders_y_texto_comun(text: str) -> None:
    assert secrets.scan_text(text) == []


def test_ignora_bloques_de_codigo_si_se_pide() -> None:
    text = f"antes\n```\n{AWS}\n```\ndespués {GITHUB}\n"
    assert [f.kind for f in secrets.scan_text(text)] == ["github-token"]
    assert [f.kind for f in secrets.scan_text(text, skip_code_blocks=False)] == ["aws-access-key", "github-token"]


def test_redacta_el_extracto() -> None:
    finding = secrets.scan_text(AWS)[0]
    assert AWS not in finding.excerpt
    assert finding.excerpt.startswith("AKIA")
