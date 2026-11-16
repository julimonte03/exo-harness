"""`exo p0`: el gate de regresión mínima (D-32, ADR-0014).

Port, redefinido, del `_verify_p0.py` del reporte. S1 (la guarda de memoria) ya no
existe (ADR-0009), así que P0 corre tres regresiones:

1. el escáner de secretos y datos personales sobre un dataset sintético;
2. la validación de entradas (S2) con entradas maliciosas;
3. los git hooks instalados y activos en el proyecto (o husky / pre-commit).

Los valores del dataset se arman en código: nada en el fuente parece un secreto o
un dato real.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from exo import _meta
from exo.core import scan
from exo.governance import githooks
from exo.tools import validation


@dataclass(frozen=True)
class Result:
    name: str
    ok: bool
    detail: str
    cases: int = 0


def _dataset() -> list[tuple[str, str | None]]:
    """`(texto, tipo esperado)`; None es un caso que no tiene que dar hallazgos."""
    aws = "AKIA" + "Z" * 16
    github = "gh" + "p_" + "x9Y8" * 9
    jwt = "eyJ" + "h" * 18 + ".eyJ" + "p" * 18 + "." + "s" * 18
    return [
        (f"key = {aws}", "aws-access-key"),
        (f"token {github}", "github-token"),
        ("-----BEGIN " + "OPENSSH PRIVATE KEY-----", "private-key"),
        ("xo" + "xp-" + "1234567890-abcdefgh", "slack-token"),
        ('password = "' + "q" * 6 + 'w9w9w9"', "credential-assignment"),
        ("DB_PASSWORD=" + "r7" * 6, "env-assignment"),
        (f"Authorization: Bearer {jwt}", "jwt"),
        ("redis://cache:" + "z1x2c3v4" + "@cache.internal:6379", "url-credentials"),
        ("Server=db;Password=" + "m3n4b5v6" + ";", "connection-string"),
        ("azure pat " + "b3" * 26, "azure-devops-pat"),
        ("4977 7777 7777 7776", "card"),
        ("DE89 3704 0044 0532 0130 00", "iban"),
        ("mail: jane.roe@acme-corp.com", "email"),
        ("tel +4915123456789", "phone"),
        ("CUIT 20-12345678-6", "ar-cuit"),
        ("DNI 28.123.456", "ar-dni"),
        ("CPF 123.456.789-09", "br-cpf"),
        ("NIF 12345678Z", "es-nif"),
        ("SSN 219-09-9998", "us-ssn"),
        ("DB_PASSWORD=${DB_PASSWORD}", None),
        ("password = '<your-password>'", None),
        ("4111 1111 1111 1111", None),
        ("GB83 WEST 1234 5698 7654 32", None),
        ("someone@example.com", None),
        ("CUIT 20-12345678-0", None),
        ("sha " + "ab12" * 10, None),
    ]


def scanner_regression() -> Result:
    cases = _dataset()
    failures: list[str] = []
    for text, expected in cases:
        kinds = {f.kind for f in scan.scan_text(text, pii=scan.KNOWN_PII)}
        if expected is None and kinds:
            failures.append(f"false positive {sorted(kinds)} in a negative case")
        elif expected is not None and expected not in kinds:
            failures.append(f"{expected} not detected")
    detail = "; ".join(failures) if failures else f"{len(cases)} cases"
    return Result("scanner", not failures, detail, len(cases))


def input_regression() -> Result:
    outside = Path(tempfile.gettempdir())
    root = outside / f"{_meta.NAME}-p0-root"
    probes = [
        ("cwd outside the root", lambda: validation.validate_cwd(str(outside), root=root)),
        ("cwd with a NUL byte", lambda: validation.validate_cwd("a\x00b")),
        ("skill name traversal", lambda: validation.validate_skill_name("../etc")),
        ("skill name with a slash", lambda: validation.validate_skill_name("a/b")),
        ("change name traversal", lambda: validation.validate_change_name("../x")),
        ("change name with a slash", lambda: validation.validate_change_name("a\\b")),
        ("change name too long", lambda: validation.validate_change_name("a" * 101)),
        (
            "unknown argument",
            lambda: validation.check_arguments(
                {"type": "object", "properties": {}, "additionalProperties": False}, {"x": 1}
            ),
        ),
    ]
    accepted = []
    for label, probe in probes:
        try:
            probe()
        except validation.InputError:
            continue
        accepted.append(label)
    detail = (
        "accepted: " + ", ".join(accepted)
        if accepted
        else f"{len(probes)} malicious inputs rejected"
    )
    return Result("input validation", not accepted, detail, len(probes))


def hooks_check(project: Path) -> Result:
    found = githooks.status(project)
    return Result("git hooks", found.status == "ok", found.detail)


def run(project: Path) -> list[Result]:
    return [scanner_regression(), input_regression(), hooks_check(project)]
