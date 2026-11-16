"""Escáner de secretos y datos personales (ADR-0014, D-12).

Dos niveles de la matriz de `data-protection.md`:

- **Crítico**: credenciales y secretos. Siempre activos y sin waiver posible.
- **Restringido**: datos personales. Los detectores activos salen de
  `data_protection.pii` en la config. Por defecto, tarjetas (Luhn) e IBAN
  (mod 97), que validan dígito y casi no dan falsos positivos. El resto (email,
  teléfono y documentos de cada país) es opcional: el motor no se ata a un país.

Ignora placeholders evidentes (`<valor>`, `${VAR}`, `xxxx`, `changeme`), las
tarjetas de prueba conocidas y, si se pide, los bloques de código. Los extractos
salen redactados. Solo biblioteca estándar.
"""

from __future__ import annotations

import fnmatch
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import PurePosixPath

CRITICAL = "critical"
RESTRICTED = "restricted"
DEFAULT_PII = ("card", "iban")
OPTIONAL_PII = ("email", "phone", "ar-cuit", "ar-dni", "br-cpf", "es-nif", "us-ssn")
KNOWN_PII = DEFAULT_PII + OPTIONAL_PII
# Archivos de credenciales: no se commitean ni se leen (los ejemplos, sí).
CREDENTIAL_FILES = (
    ".env",
    ".env.*",
    "*.pem",
    "*.p12",
    "*.pfx",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
)
CREDENTIAL_EXAMPLES = (".env.example", ".env.sample", ".env.template")

_PLACEHOLDER = re.compile(
    r"^(?:<.*>|\$\{.*\}|\$[A-Za-z_][A-Za-z0-9_]*|%[A-Za-z_]+%|x+|\*+|changeme|example.*|dummy.*"
    r"|your[-_].*|placeholder.*)$",
    re.IGNORECASE,
)
_FENCE = re.compile(r"^\s*(```|~~~)")
# Palabras completas entre guiones bajos: `PAT` no es la subcadena de PATH ni de COMPAT.
_SECRET_WORDS = r"(?:PASSWORD|PASSWD|SECRET|TOKEN|API_?KEY|ACCESS_KEY|PRIVATE_KEY|PAT)"
# Tarjetas de prueba publicadas por las redes y los procesadores de pago: no son datos reales.
_TEST_CARDS = frozenset(
    {
        "4111111111111111",
        "4242424242424242",
        "4012888888881881",
        "4000056655665556",
        "5555555555554444",
        "5105105105105100",
        "2223003122003222",
        "378282246310005",
        "371449635398431",
        "6011111111111117",
        "3530111333300000",
        "30569309025904",
    }
)
_TEST_DOMAINS = re.compile(
    r"(?:^|\.)(?:example\.(?:com|org|net)|example|test|invalid|localhost|local)$", re.IGNORECASE
)


@dataclass(frozen=True)
class Finding:
    line: int
    kind: str
    level: str  # critical | restricted
    excerpt: str


@dataclass(frozen=True)
class _Detector:
    kind: str
    level: str
    pattern: re.Pattern[str]
    group: int = 0
    valid: Callable[[str], bool] | None = None
    placeholders: bool = False
    context: re.Pattern[str] | None = None


# -- validadores ------------------------------------------------------------------------------


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def _luhn(value: str) -> bool:
    digits = _digits(value)
    if not 13 <= len(digits) <= 19 or digits in _TEST_CARDS or len(set(digits)) == 1:
        return False
    total = 0
    for index, char in enumerate(reversed(digits)):
        digit = int(char)
        if index % 2 == 1:
            digit *= 2
            digit = digit - 9 if digit > 9 else digit
        total += digit
    return total % 10 == 0


def _iban(value: str) -> bool:
    text = re.sub(r"\s", "", value).upper()
    if not 15 <= len(text) <= 34:
        return False
    moved = text[4:] + text[:4]
    number = "".join(str(int(c, 36)) for c in moved)
    return int(number) % 97 == 1


def _email(value: str) -> bool:
    domain = value.rsplit("@", 1)[1]
    return _TEST_DOMAINS.search(domain) is None


def _cuit(value: str) -> bool:
    digits = _digits(value)
    weights = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
    rest = 11 - sum(int(d) * w for d, w in zip(digits[:10], weights, strict=True)) % 11
    return {11: 0, 10: 9}.get(rest, rest) == int(digits[10])


def _cpf(value: str) -> bool:
    digits = [int(d) for d in _digits(value)]
    if len(set(digits)) == 1:
        return False
    for size in (9, 10):
        total = sum(d * w for d, w in zip(digits[:size], range(size + 1, 1, -1), strict=True))
        if (0 if total % 11 < 2 else 11 - total % 11) != digits[size]:
            return False
    return True


def _nif(value: str) -> bool:
    text = re.sub(r"[\s-]", "", value).upper()
    head = text[:-1].replace("X", "0", 1).replace("Y", "1", 1).replace("Z", "2", 1)
    return head.isdigit() and "TRWAGMYFPDXBNJZSQVHLCKE"[int(head) % 23] == text[-1]


_SECRETS = (
    _Detector("aws-access-key", CRITICAL, re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    _Detector(
        "github-token",
        CRITICAL,
        re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,})\b"),
    ),
    _Detector("private-key", CRITICAL, re.compile(r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----")),
    _Detector("slack-token", CRITICAL, re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    _Detector(
        "credential-assignment",
        CRITICAL,
        re.compile(
            r"(?i)\b(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|client[_-]?secret)\b"
            r"\s*[:=]\s*(['\"])([^'\"\s]{8,})\1"
        ),
        group=2,
        placeholders=True,
    ),
    _Detector(
        "env-assignment",
        CRITICAL,
        re.compile(
            rf"^\s*(?:export\s+)?(?:[A-Z][A-Z0-9]*_)*{_SECRET_WORDS}(?:_[A-Z0-9]+)*"
            rf"\s*=\s*([^\s'\"#]{{8,}})"
        ),
        group=1,
        placeholders=True,
    ),
    # Claves sin comillas de properties y YAML (`spring.datasource.password=...`,
    # `password: ...`): el valor necesita letras y dígitos, para no tomar "required".
    _Detector(
        "credential-assignment",
        CRITICAL,
        re.compile(
            r"(?i)^\s*(?:[a-z0-9_-]+[._-])*(?:password|passwd|secret|token|api[_-]?key"
            r"|client[_-]?secret)\s*[:=]\s*([^\s'\"#,;{}\[\]]{8,})\s*$"
        ),
        group=1,
        placeholders=True,
        valid=lambda value: any(c.isdigit() for c in value) and any(c.isalpha() for c in value),
    ),
    _Detector(
        "jwt",
        CRITICAL,
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    ),
    _Detector(
        "url-credentials",
        CRITICAL,
        re.compile(r"\b[a-z][a-z0-9+.-]*://[^/\s:@]+:([^/\s@]{4,})@"),
        group=1,
        placeholders=True,
    ),
    _Detector(
        "connection-string",
        CRITICAL,
        re.compile(r"(?i)\b(?:password|pwd)\s*=\s*([^;'\"\s]{4,})\s*;"),
        group=1,
        placeholders=True,
    ),
    _Detector(
        "azure-devops-pat",
        CRITICAL,
        re.compile(r"\b[a-z2-7]{52}\b"),
        context=re.compile(r"(?i)azure|devops|\bado\b|\bpat\b"),
    ),
)
_PII = {
    "card": _Detector(
        "card", RESTRICTED, re.compile(r"(?<![\w-])[2-6](?:[ -]?\d){12,18}(?![\w-])"), valid=_luhn
    ),
    "iban": _Detector(
        "iban",
        RESTRICTED,
        re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]){11,30}\b"),
        valid=_iban,
    ),
    "email": _Detector(
        "email",
        RESTRICTED,
        re.compile(r"\b[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}\b"),
        valid=_email,
    ),
    "phone": _Detector("phone", RESTRICTED, re.compile(r"(?<![\w.])\+[1-9](?:[ -]?\d){7,14}\b")),
    "ar-cuit": _Detector(
        "ar-cuit", RESTRICTED, re.compile(r"\b(?:20|23|24|27|30|33|34)-?\d{8}-?\d\b"), valid=_cuit
    ),
    "ar-dni": _Detector(
        "ar-dni",
        RESTRICTED,
        re.compile(r"(?i)\bDNI\b\D{0,5}(\d{1,2}\.?\d{3}\.?\d{3})\b"),
        group=1,
    ),
    "br-cpf": _Detector(
        "br-cpf", RESTRICTED, re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), valid=_cpf
    ),
    "es-nif": _Detector(
        "es-nif", RESTRICTED, re.compile(r"\b(?:\d{8}|[XYZ]-?\d{7})-?[A-Z]\b"), valid=_nif
    ),
    "us-ssn": _Detector(
        "us-ssn", RESTRICTED, re.compile(r"\b(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b")
    ),
}


def _redact(value: str) -> str:
    """Como mucho 4 caracteres y nunca más de un tercio: un secreto corto no sale entero."""
    return value[: min(4, len(value) // 3)] + "…"


def _detectors(pii: Iterable[str], secrets: bool) -> list[_Detector]:
    chosen = list(_SECRETS) if secrets else []
    for name in pii:
        if name not in _PII:
            raise ValueError(
                f"unknown personal-data detector: {name} (known: {', '.join(KNOWN_PII)})"
            )
        chosen.append(_PII[name])
    return chosen


def _scan_line(number: int, line: str, detectors: list[_Detector]) -> list[Finding]:
    found: list[Finding] = []
    seen: set[tuple[int, int]] = set()  # el mismo valor, tomado por dos detectores, una vez
    for detector in detectors:
        if detector.context is not None and not detector.context.search(line):
            continue
        for match in detector.pattern.finditer(line):
            value = match.group(detector.group)
            if detector.placeholders and _PLACEHOLDER.match(value):
                continue
            if detector.valid is not None and not detector.valid(value):
                continue
            span = match.span(detector.group)
            if span in seen:
                continue
            seen.add(span)
            found.append(Finding(number, detector.kind, detector.level, _redact(value)))
    return found


def scan_lines(
    lines: Iterable[tuple[int, str]], *, pii: Iterable[str] = DEFAULT_PII, secrets: bool = True
) -> list[Finding]:
    """Escanea `(número, texto)` sueltos, por ejemplo las líneas agregadas de un diff."""
    detectors = _detectors(pii, secrets)
    found: list[Finding] = []
    for number, line in lines:
        found.extend(_scan_line(number, line, detectors))
    return found


def scan_text(
    text: str,
    *,
    skip_code_blocks: bool = True,
    pii: Iterable[str] = DEFAULT_PII,
    secrets: bool = True,
) -> list[Finding]:
    detectors = _detectors(pii, secrets)
    found: list[Finding] = []
    in_code = False
    for number, line in enumerate(text.splitlines(), start=1):
        if _FENCE.match(line):
            in_code = not in_code
            continue
        if in_code and skip_code_blocks:
            continue
        found.extend(_scan_line(number, line, detectors))
    return found


def is_credential_file(path: str) -> bool:
    """Un archivo con nombre de credencial (`.env`, claves privadas), salvo los ejemplos."""
    name = PurePosixPath(path.replace("\\", "/")).name
    if name in CREDENTIAL_EXAMPLES:
        return False
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in CREDENTIAL_FILES)
