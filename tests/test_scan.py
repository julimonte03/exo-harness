"""core/scan: secretos (Crítico, siempre) y datos personales (Restringido, según la config), D-12.

Todos los valores son sintéticos y se arman en el test: los números de tarjeta,
IBAN y documentos se calculan con su dígito verificador, nunca son reales.
"""

from __future__ import annotations

import pytest

from exo.core import scan

AWS = "AKIA" + "Q" * 16
JWT = "eyJ" + "a" * 20 + ".eyJ" + "b" * 20 + "." + "c" * 20


def luhn(prefix: str, length: int) -> str:
    """Un número que pasa Luhn, armado a partir de un prefijo."""
    body = (prefix + "7" * length)[: length - 1]
    total = 0
    for index, char in enumerate(reversed(body)):
        digit = int(char)
        if index % 2 == 0:
            digit *= 2
            digit = digit - 9 if digit > 9 else digit
        total += digit
    return body + str((10 - total % 10) % 10)


def cuit(prefix: str, number: str) -> str:
    digits = prefix + number
    weights = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
    rest = 11 - sum(int(d) * w for d, w in zip(digits, weights, strict=True)) % 11
    check = {11: 0, 10: 9}.get(rest, rest)
    return f"{prefix}-{number}-{check}"


def cpf(nine: str) -> str:
    digits = [int(d) for d in nine]
    for size in (10, 11):
        total = sum(d * w for d, w in zip(digits, range(size, 1, -1), strict=False))
        digits.append(0 if total % 11 < 2 else 11 - total % 11)
    text = "".join(map(str, digits))
    return f"{text[:3]}.{text[3:6]}.{text[6:9]}-{text[9:]}"


def nif(number: str) -> str:
    return number + "TRWAGMYFPDXBNJZSQVHLCKE"[int(number) % 23]


CARD = luhn("49", 16)
SPACED_CARD = " ".join(CARD[i : i + 4] for i in range(0, 16, 4))
IBAN = "GB82 WEST 1234 5698 7654 32"  # el ejemplo de la norma ISO 13616


def _kinds(text: str, **kwargs: object) -> list[tuple[int, str, str]]:
    return [(f.line, f.kind, f.level) for f in scan.scan_text(text, **kwargs)]


# -- secretos (Crítico, siempre activos) -------------------------------------------------


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        (f"key = {AWS}", "aws-access-key"),
        ('password = "s3cr3t-valor-largo"', "credential-assignment"),
        ("DB_PASSWORD=hunter2hunter2", "env-assignment"),
        ("export API_TOKEN=abcd1234efgh5678", "env-assignment"),
        (f"Authorization: Bearer {JWT}", "jwt"),
        ("postgres://app:s3cr3tpass@db.internal:5432/app", "url-credentials"),
        ("Server=db;User Id=app;Password=s3cr3tpass;", "connection-string"),
        ("AZURE_DEVOPS_PAT=" + "a2" * 26, "env-assignment"),
        ("azure pat: " + "a2" * 26, "azure-devops-pat"),
    ],
)
def test_secretos(text: str, kind: str) -> None:
    found = _kinds(f"line one\n{text}\n", pii=())
    assert (2, kind, "critical") in found, found


@pytest.mark.parametrize(
    "text",
    [
        "DB_PASSWORD=${DB_PASSWORD}",
        "DB_PASSWORD=changeme",
        "export API_TOKEN=<your-token>",
        "postgres://user:${PASS}@db/app",
        "postgres://localhost:5432/app",
        "a2" * 26,  # sin contexto no es un PAT
        "sha: " + "ab12" * 10,
    ],
)
def test_no_son_secretos(text: str) -> None:
    assert _kinds(text, pii=()) == []


def test_los_extractos_salen_redactados() -> None:
    [finding] = scan.scan_text("DB_PASSWORD=hunter2hunter2", pii=())
    assert "hunter2hunter2" not in finding.excerpt
    assert finding.excerpt.endswith("…")


# -- datos personales (Restringido, según la config) ---------------------------------------


@pytest.mark.parametrize(
    ("text", "kind", "pii"),
    [
        (f"card: {CARD}", "card", ("card",)),
        (f"card: {SPACED_CARD}", "card", ("card",)),
        (f"account {IBAN}", "iban", ("iban",)),
        ("contact: ana.perez@acme-corp.com", "email", ("email",)),
        ("call +5491155550123 now", "phone", ("phone",)),
        (f"CUIT {cuit('20', '12345678')}", "ar-cuit", ("ar-cuit",)),
        ("DNI 30123456", "ar-dni", ("ar-dni",)),
        (f"CPF {cpf('123456789')}", "br-cpf", ("br-cpf",)),
        (f"NIF {nif('12345678')}", "es-nif", ("es-nif",)),
        ("SSN 219-09-9998", "us-ssn", ("us-ssn",)),
    ],
)
def test_datos_personales(text: str, kind: str, pii: tuple[str, ...]) -> None:
    assert (1, kind, "restricted") in _kinds(text, pii=pii)


@pytest.mark.parametrize(
    ("text", "pii"),
    [
        (CARD[:-1] + str((int(CARD[-1]) + 1) % 10), ("card",)),  # no pasa Luhn
        ("4111 1111 1111 1111", ("card",)),  # tarjeta de prueba conocida
        ("GB83 WEST 1234 5698 7654 32", ("iban",)),  # dígito de control mal
        ("contact: someone@example.com", ("email",)),
        ("version 1.2.3.4567", ("phone",)),
        ("20-12345678-0", ("ar-cuit",)),  # dígito mal (el bueno no es 0)
        ("id 30123456 without context", ("ar-dni",)),
        ("123.456.789-00", ("br-cpf",)),
        ("12345678A", ("es-nif",)),
        ("SSN 000-12-3456", ("us-ssn",)),
        (f"card: {CARD}", ()),  # detector apagado
    ],
)
def test_no_son_datos_personales(text: str, pii: tuple[str, ...]) -> None:
    assert _kinds(text, pii=pii) == []


def test_los_defaults_son_tarjeta_e_iban() -> None:
    assert scan.DEFAULT_PII == ("card", "iban")
    assert {k for _, k, _ in _kinds(f"{CARD}\n{IBAN}\nDNI 30123456\n")} == {"card", "iban"}


def test_detector_desconocido() -> None:
    with pytest.raises(ValueError, match="unknown"):
        scan.scan_text("x", pii=("passport",))


def test_bloques_de_codigo_y_lineas_sueltas() -> None:
    text = f"```\n{AWS}\n```\n"
    assert _kinds(text, pii=()) == []
    assert _kinds(text, pii=(), skip_code_blocks=False) == [(2, "aws-access-key", "critical")]
    found = scan.scan_lines([(10, f"+{AWS}"), (11, "nada")], pii=())
    assert [(f.line, f.kind) for f in found] == [(10, "aws-access-key")]


def test_la_fachada_de_secrets_sigue_igual() -> None:
    from exo.core import secrets

    [finding] = secrets.scan_text(f"x {AWS}\n{CARD}\n")
    assert (finding.line, finding.kind) == (1, "aws-access-key")


def test_una_tira_de_digitos_dentro_de_un_hash_no_es_tarjeta() -> None:
    """Bug de F5: el hash de un archivo en lock.json bloqueaba el commit de `exo init`."""
    card = "4977777777777776"  # sintética, pasa Luhn
    assert [f.kind for f in scan.scan_text(f"card {card}")] == ["card"]
    for text in (
        f'"sha256": "a243820deca498e6d753ace61073{card}9bd5b25ea0916770040522a6"',
        f"id_{card}",
        f"{card}abc",
    ):
        assert scan.scan_text(text) == [], text


@pytest.mark.parametrize(
    "text",
    [
        "export PYTHONPATH=/app/src",
        "LD_LIBRARY_PATH=/usr/local/lib",
        "CLASSPATH=lib/foo.jar:lib/bar.jar",
        "GOPATH=$HOME/go",
        "COMPAT_MODE=enabled1",
        "Password: required",
        "token: optional",
    ],
)
def test_env_y_claves_sin_falsos_positivos(text: str) -> None:
    """Revisión de cierre: `PAT` como subcadena de PATH o COMPAT daba un Crítico sin waiver."""
    assert _kinds(text, pii=()) == []


@pytest.mark.parametrize(
    "text",
    [
        "PASSWORD=hunter2hunter2",
        "API_KEY=sk9live9abcdefgh",
        "SECRET=s3cr3t-value-x",
        "TOKEN=tok3n-abcdefgh",
        "spring.datasource.password=MySecret123",
        "password: MySecret123",
        "  db_token: Zx9y8w7v6u",
        "GITHUB_PAT=ghx9y8w7v6u5t4",
    ],
)
def test_claves_sin_prefijo_o_en_minuscula_se_detectan(text: str) -> None:
    kinds = [kind for _, kind, _ in _kinds(text, pii=())]
    assert kinds in (["env-assignment"], ["credential-assignment"]), text


def test_un_secreto_corto_no_sale_entero_en_el_extracto() -> None:
    [finding] = scan.scan_text("Server=db;Password=abcd;", pii=())
    assert finding.excerpt == "a…"
    [finding] = scan.scan_text("redis://cache:k9z8y7@cache.internal:6379", pii=())
    assert finding.excerpt == "k9…"


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        ".ENV",
        "config/.Env.Production",
        "certs/server.PEM",
        "ID_RSA",
        "keys/signing.key",
        "android/release.jks",
        "android/debug.keystore",
        "putty/server.ppk",
        ".pypirc",
        ".netrc",
        "credentials.json",
        "gcp/Credentials.json",
    ],
)
def test_archivos_de_credenciales(path: str) -> None:
    """L4: sin distinguir mayúsculas, con las claves y los archivos de tokens de registros."""
    assert scan.is_credential_file(path), path


@pytest.mark.parametrize(
    "path",
    [
        ".env.example",
        ".ENV.Sample",
        "app.py",
        "keyboard.py",
        "credentials.py",
        "monkey.js",
        ".npmrc",
    ],
)
def test_no_son_archivos_de_credenciales(path: str) -> None:
    assert not scan.is_credential_file(path), path


def test_timestamps_e_ids_largos_no_son_tarjetas() -> None:
    """Un timestamp en milisegundos (13 dígitos que empiezan con 1) no es una tarjeta."""
    stamps = [str(1_700_000_000_000 + n * 7_919) for n in range(200)]
    assert all(scan.scan_text(s) == [] for s in stamps)
    assert scan.scan_text("id 9" + "0" * 17 + "8") == []
