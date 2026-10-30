"""Escáner mínimo de secretos en texto.

Lo usa `exo validate` sobre el contenido. F3 lo extiende como guard S1 de la
memoria (con perfiles de PII) y F5 lo reusa en el hook `pre-commit`. Ignora
placeholders evidentes (`<valor>`, `${VAR}`, `xxxx`, `changeme`) y, si se pide,
el contenido de bloques de código. Los extractos salen redactados.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    (
        "github-token",
        re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,})\b"),
    ),
    ("private-key", re.compile(r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----")),
    ("slack-token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    (
        "credential-assignment",
        re.compile(
            r"(?i)\b(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|client[_-]?secret)\b"
            r"\s*[:=]\s*(['\"])([^'\"\s]{8,})\1"
        ),
    ),
)
_PLACEHOLDER = re.compile(
    r"^(?:<.*>|\$\{.*\}|\$[A-Z_][A-Z0-9_]*|x+|\*+|changeme|example.*|dummy.*|your[-_].*)$",
    re.IGNORECASE,
)
_FENCE = re.compile(r"^\s*(```|~~~)")


@dataclass(frozen=True)
class SecretFinding:
    line: int
    kind: str
    excerpt: str


def _redact(value: str) -> str:
    return value[:4] + "…"


def scan_text(text: str, *, skip_code_blocks: bool = True) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    in_code = False
    for number, line in enumerate(text.splitlines(), start=1):
        if _FENCE.match(line):
            in_code = not in_code
            continue
        if in_code and skip_code_blocks:
            continue
        for kind, pattern in _PATTERNS:
            for match in pattern.finditer(line):
                value = match.group(2) if kind == "credential-assignment" else match.group(0)
                if kind == "credential-assignment" and _PLACEHOLDER.match(value):
                    continue
                findings.append(SecretFinding(number, kind, _redact(value)))
    return findings
