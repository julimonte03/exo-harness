"""Validador del contenido canónico (`exo validate`).

Reglas de §10.5 del reporte, adaptadas al plan (`docs/plan/fases/F1-nucleo.md`):

- Manifiestos de pack: nombre kebab-case igual a la carpeta, semver,
  descripción; `requires` existentes y sin ciclos.
- Skills: frontmatter estricto del estándar Agent Skills (solo `name`,
  `description`, `license`, `compatibility`, `metadata`, `allowed-tools`; lo
  propio va en `metadata`), `name` igual a la carpeta, kebab-case y hasta 64
  caracteres, `description` hasta 1024, nombres únicos en la colección, sin
  escapes `\\uXXXX` literales, `references/` citados existentes y advertencia si
  `SKILL.md` supera 500 líneas.
- Referencias `skill:<nombre>` resolubles y declaradas en `requires`/`optional`.
  Una que no resuelve es error, salvo que el mapa fase → skills la declare entre
  las skills de packs que todavía no existen (`phase_map`), con un pack que el
  pack de la referencia declare: ahí la skill degrada inline (F4).
- Contratos compartidos (`packs/<pack>/shared/`): los JSON parsean y los de
  `schemas/` usan solo lo que soporta `core/jsonschema`; los `.md` siguen las
  mismas reglas de cuerpo que las skills. Toda ruta a un contrato instalado
  (`<carpeta del motor>/shared/...`) que citen las skills, sus `references/` o los
  contratos tiene que existir en el pack que cita o en uno que requiere: si no,
  falta cuando solo ese pack está instalado.
- Subagentes con `name` y `description`, sin repetir.
- `rules/AGENTS.base.md` de hasta 60 líneas.
- Sin patrones de secretos fuera de bloques de código.
- Pre-chequeo de instrucciones sospechosas (F5): advertencias, no errores, porque
  una skill puede describir un ataque con buenos motivos y lo decide una persona
  con la skill `skill-reviewer`. Revisa `SKILL.md`, los archivos de texto de sus
  `references/` y los subagentes (`packs/<pack>/agents/`), línea por línea, con
  el frontmatter y los bloques de código incluidos (un `curl | sh` suele estar en
  un bloque). Busca inyección de prompt (pisar o esconder las instrucciones),
  descargar y ejecutar, envío de datos a una URL que no es loopback, pedidos a la
  persona de credenciales o documentos (exigen un verbo de pedido dirigido a ella
  y un dato sensible, y no cuentan con una negación antes en la misma frase) y
  caracteres invisibles (ancho cero, control bidi y etiquetas Unicode). Cada
  advertencia dice qué encontró, por qué es riesgoso y qué hacer; la de envío no
  repite los datos y la de invisibles nombra el carácter en vez de copiarlo.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from exo import _meta, phase_map
from exo.core import frontmatter, fsutil, jsonschema, secrets
from exo.installer.bundle import ENGINE_SHARED, ENGINE_SHARED_PACK
from exo.packs import MANIFEST, SKILL_FILE, Pack, PackError, load_pack, resolve

STANDARD_FIELDS = ("name", "description", "license", "compatibility", "metadata", "allowed-tools")
MAX_NAME = 64
MAX_DESCRIPTION = 1024
MAX_COMPATIBILITY = 500
MAX_SKILL_LINES = 500
MAX_RULE_LINES = 60
RULES_FILE = Path("rules") / "AGENTS.base.md"
_SCANNED = {".md", ".json", ".txt", ".yml", ".yaml", ".toml"}
# Scripts que una skill puede traer: el pre-chequeo los lee también.
_SCRIPTS = {".sh", ".bash", ".zsh", ".py", ".ps1", ".psm1", ".bat", ".cmd", ".js", ".mjs", ".ts"}
_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_ESCAPE = re.compile(r"\\u[0-9a-fA-F]{4}")
_SKILL_REF = re.compile(r"\bskill:([a-z0-9][a-z0-9-]*)")
# Rutas relativas a la skill; no cuenta dentro de URLs ni de otras rutas (x/references/...).
_REFERENCE_FILE = re.compile(r"(?<![\w/.:-])references/[^\s)\]'\"`<>]+")
_FENCE = re.compile(r"^\s*(```|~~~)")
SHARED_DIR = "shared"
_SHARED_PATH = re.compile(rf"{re.escape(_meta.PROJECT_DIR)}/shared/([A-Za-z0-9._/-]+)")


# -- instrucciones sospechosas (F5) ---------------------------------------------------------
#
# Heurísticas por línea, sin distinguir mayúsculas salvo las opciones de curl y wget
# (-F no es -f). Apuntan a cero falsos positivos sobre el contenido del motor: por eso
# los pedidos exigen un verbo dirigido a la persona más un dato sensible.

INJECTION = "prompt injection"
DOWNLOAD_EXEC = "download and execute"
UPLOAD = "data sent to a URL"
CREDENTIAL_REQUEST = "credential or document request"
INVISIBLE = "invisible characters"
_I = re.IGNORECASE
_MAX_EXCERPT = 80

# Pisar las instrucciones del agente o esconderle algo a la persona.
_TARGET = r"(?:your|my|our|previous|prior|above|earlier|preceding|former|initial|original|system)"
_ORDERS = r"(?:instructions?|prompts?|rules|directions|directives|guidelines|guidance)"
_INJECTION = (
    re.compile(
        r"\b(?:ignore|disregard|forget)\s+(?:(?:all|any|every|the|of|about|these|those)\s+)*"
        rf"{_TARGET}\s+(?:(?:previous|prior|earlier|system|original|initial)\s+)?{_ORDERS}\b",
        _I,
    ),
    # "You are no longer bound by...", no "you're no longer finding anything new".
    re.compile(
        r"\byou(?:\s+are|['’]re)\s+no\s+longer\s+(?:bound|restricted|limited|required|obliged"
        r"|obligated|subject|governed|constrained|under|an?|the|claude|chatgpt|gpt|ai)\b",
        _I,
    ),
    # Esconderle algo a la persona; "don't tell the user to run X" es otra cosa.
    re.compile(
        r"\b(?:do\s+not|don['’]t)\s+(?:tell|inform|notify|alert)\s+(?:the\s+)?(?:user|human)s?\b"
        r"(?!\s+to\b)",
        _I,
    ),
    # "without informing the user" describe errores silenciosos en una revisión de código.
    re.compile(
        r"\bwithout\s+telling\s+(?:the\s+)?(?:user|human)s?\b"
        r"|\bwithout\s+the\s+(?:user|human)s?['’]?s?\s+(?:knowing|noticing|knowledge)\b",
        _I,
    ),
)

# Descargar y ejecutar en el mismo paso.
_FETCH = r"(?:curl|wget)(?:\.exe)?"
_SHELL = r"(?:ba|z|da|k|fi)?sh"
_INTERPRETER = r"(?:python[23]?|perl|ruby|node)"
_SUDO = r"(?:sudo\s+(?:-\S+\s+)*)?"
_PS_FETCH = r"(?:iwr|irm|invoke-webrequest|invoke-restmethod|curl|wget)"
_DOWNLOAD_EXEC = (
    re.compile(rf"(?<![\w.-]){_FETCH}\b[^|\n]*\|\s*{_SUDO}{_SHELL}\b(?![.-])", _I),
    re.compile(
        rf"(?<![\w.-]){_FETCH}\b[^|\n]*\|\s*{_SUDO}{_INTERPRETER}(?:\s+-)?\s*(?:$|[;&|)`'\"])", _I
    ),
    re.compile(
        rf"(?:\b{_SHELL}|\b{_INTERPRETER}|\bsource|(?<!\S)\.)\s+(?:-\S+\s+)*<\(\s*{_FETCH}\b", _I
    ),
    re.compile(
        rf"(?:\b{_SHELL}|\b{_INTERPRETER})\s+(?:-\S+\s+)*-c\s+[\"']?\$\(\s*{_FETCH}\b"
        rf"|\beval\s+[\"']?\$\(\s*{_FETCH}\b",
        _I,
    ),
    re.compile(rf"\b{_PS_FETCH}\b[^|\n]*\|\s*(?:iex|invoke-expression)\b", _I),
    re.compile(
        r"\b(?:iex|invoke-expression)\b.*?\b(?:iwr|irm|invoke-webrequest|invoke-restmethod"
        r"|downloadstring|downloaddata|downloadfile|net\.webclient|start-bitstransfer|curl|wget)\b",
        _I,
    ),
)

# Enviar datos con curl o wget a una URL que no es loopback.
_FETCH_TOOL = re.compile(rf"(?<![\w.-])({_FETCH})\b", _I)
_COMMAND_END = re.compile(r"\|\||&&|[|;]")
_DATA_FLAG = re.compile(
    r"(?<!\S)(-d|-F|-T|--data(?:-binary|-raw|-urlencode|-ascii)?|--json|--form(?:-string)?"
    r"|--upload-file|--post-data|--post-file|--body-data|--body-file)(?=[\s=@'\"]|$)"
)
_URL = re.compile(r"(https?)://([^\s/'\"`<>)\]]+)", _I)
_LOOPBACK = re.compile(r"^(?:localhost|127(?:\.\d{1,3}){3}|\[::1\]|0\.0\.0\.0)(?::\d+)?$", _I)

# Pedirle a la persona un dato sensible: verbo de pedido dirigido a ella + el dato.
_SENSITIVE = (
    r"(?:passwords?|passphrases?|passcodes?|pins?"
    r"|(?:api|access|secret|private|ssh|signing|encryption)[\s_-]?keys?|apikeys?"
    r"|tokens?|secrets?|credentials?"
    r"|(?:seed|recovery|mnemonic)[\s-]phrases?|mnemonics?"
    r"|(?:one[\s-]time|otp|2fa|mfa|verification|security)\s+codes?"
    r"|(?:credit[\s-]card|debit[\s-]card|card|bank[\s-]account|account)\s+numbers?|cvvs?|cvcs?"
    r"|social\s+security\s+numbers?|ssns?"
    r"|(?:national\s+)?id(?:entity)?\s+(?:cards?|documents?|numbers?)|passports?(?:\s+numbers?)?"
    r"|driver['’]?s?\s+licen[cs]es?|tax\s+ids?|dnis?|cuits?|cuils?|cpfs?)"
    # El dato es el núcleo de la frase, no un modificador ("password policy", "token's scopes").
    r"(?![\w-])(?!['’]s\b)(?!\s+(?:format|type|name|expir\w*|scopes?|length|polic\w*|rules?"
    r"|requirements?|rotation|managers?|stores?|vaults?|fields?|prompts?|variables?|env\w*"
    r"|files?|paths?|ids?|headers?|permissions?|settings?|pages?|hash\w*|resets?|strength"
    r"|changes?|placeholders?|helpers?)\b)"
)
_STOP = (
    r"(?:the|a|an|to|and|or|but|of|for|from|in|into|on|at|by|with|it|its|this|that|these"
    r"|those|me|us|them|is|are|was|be|if|when|so|then|not|never|no)"
)
# Hasta tres palabras entre el posesivo y el dato ("your GitHub personal access token").
_GAP = rf"(?:(?!{_STOP}\b)[\w'’-]+\s+){{0,3}}?"
_GIVE_DIRECT = r"(?:paste|share|provide|submit|upload|post|attach|reply\s+with|respond\s+with)"
_GIVE_TO = r"(?:send|give|tell|hand(?:\s+over)?|forward|email|show|read\s+out|message|dm)"
_GIVE = rf"(?:{_GIVE_DIRECT}|{_GIVE_TO})"
_ME = r"(?:me|us)"
_PEOPLE = r"(?:users?|persons?|people|humans?|developers?|customers?|clients?|operators?)"
_REQUESTS = (
    # paste your token · provide us with your credentials · reply with your SSN
    re.compile(
        rf"\b{_GIVE_DIRECT}\s+(?:(?:it\s+)?(?:to|with)\s+{_ME}\s+|{_ME}\s+(?:with\s+)?)?"
        rf"your\s+{_GAP}{_SENSITIVE}",
        _I,
    ),
    # send us your password · give me your private key
    re.compile(rf"\b{_GIVE_TO}\s+{_ME}\s+(?:with\s+)?your\s+{_GAP}{_SENSITIVE}", _I),
    # send your password to us
    re.compile(rf"\b{_GIVE}\s+your\s+{_GAP}{_SENSITIVE}\s+(?:over\s+)?to\s+{_ME}\b", _I),
    # ask the user for their API key · have the person paste their token
    re.compile(
        rf"\b(?:ask|request|have|make|get|tell|instruct|remind|invite)\s+"
        rf"(?:(?:the\s+)?{_PEOPLE}|them|him|her)\s+"
        rf"(?:for\s+|(?:to\s+)?{_GIVE}\s+(?:(?:{_ME}|it)\s+)?(?:(?:to|with)\s+{_ME}\s+)?)"
        rf"(?:(?:their|his|her|your|the|a|an|any)\s+)?{_GAP}{_SENSITIVE}",
        _I,
    ),
    # collect the user's credentials
    re.compile(
        rf"\b(?:ask\s+for|request|collect|gather|harvest)\s+(?:the\s+)?{_PEOPLE}['’]s?\s+"
        rf"{_GAP}{_SENSITIVE}",
        _I,
    ),
    # the user needs to send us their secret key
    re.compile(
        rf"\b{_PEOPLE}\s+(?:must|should|needs?\s+to|has\s+to|have\s+to)\s+{_GIVE}\s+"
        rf"(?:{_ME}|(?:it\s+)?(?:to|with)\s+{_ME})\s+(?:their|his|her|your)\s+{_GAP}{_SENSITIVE}",
        _I,
    ),
)
# Una negación antes del pedido, en la misma frase, lo vuelve una regla de qué no hacer.
_NEGATION = re.compile(
    r"\b(?:never|not|no|nor|cannot|without|avoid|refuse|stop|forbid\w*|prohibit\w*)\b|n['’]t\b",
    _I,
)
_CLAUSE_BREAK = re.compile(r"[.;!?|]|:\s")

# Ancho cero, controles bidi y etiquetas Unicode: texto que el agente lee y una persona no ve.
_INVISIBLE_RANGES = ((0x200B, 0x200F), (0x202A, 0x202E), (0x2066, 0x2069), (0xE0000, 0xE007F))
_INVISIBLE = re.compile(
    "[" + "".join(f"{chr(first)}-{chr(last)}" for first, last in _INVISIBLE_RANGES) + "]"
)

_WHY = {
    INJECTION: (
        "it tells the agent to drop its instructions or to hide what it does from the person, "
        "so the skill can take over the session",
        "Remove it; if the skill only describes this attack, describe it without the literal "
        "phrase",
    ),
    DOWNLOAD_EXEC: (
        "it runs code fetched from the network without review or a pinned version",
        "Download to a file, check its checksum or signature, review it and run it as a "
        "separate step, or use the package manager",
    ),
    UPLOAD: (
        "it sends local files or data to a remote server, which can leak code, secrets or "
        "personal data",
        "Remove it, or name the destination and the data and make sure the project enables "
        "that destination explicitly",
    ),
    CREDENTIAL_REQUEST: (
        "it asks the person for a credential or an identity document, which must never reach "
        "the chat, the model or memory (Critical and Restricted data)",
        "Remove it; tools read credentials from an environment variable or a secret store, "
        "never from the conversation",
    ),
    INVISIBLE: (
        "zero-width and bidirectional control characters hide or reorder text, so the agent "
        "reads instructions a reviewer does not see",
        "Remove them",
    ),
}


def _quoted(text: str) -> str:
    text = text.strip()
    if len(text) > _MAX_EXCERPT:
        text = text[: _MAX_EXCERPT - 3] + "..."
    return f'"{text}"'


def _first_match(patterns: tuple[re.Pattern[str], ...]) -> Callable[[str], str | None]:
    def detect(line: str) -> str | None:
        for pattern in patterns:
            found = pattern.search(line)
            if found:
                return _quoted(found.group())
        return None

    return detect


def _upload(line: str) -> str | None:
    """`curl -d ... https://host`: nombra la herramienta, la opción y el host, nunca los datos."""
    for tool in _FETCH_TOOL.finditer(line):
        rest = line[tool.end() :]
        end = _COMMAND_END.search(rest)
        command = rest[: end.start()] if end else rest
        flag = _DATA_FLAG.search(command)
        if flag is None:
            continue
        for url in _URL.finditer(command):
            host = url.group(2).rsplit("@", 1)[-1]
            if not _LOOPBACK.match(host):
                return _quoted(f"{tool.group(1)} {flag.group(1)} ... {url.group(1)}://{host}")
    return None


def _credential_request(line: str) -> str | None:
    for pattern in _REQUESTS:
        for found in pattern.finditer(line):
            clause = _CLAUSE_BREAK.split(line[: found.start()])[-1]
            if not _NEGATION.search(clause):
                return _quoted(found.group())
    return None


def _invisible(line: str) -> str | None:
    """Nombra cada carácter invisible (sin copiarlo) con su columna; hasta tres."""
    seen: dict[str, int] = {}
    for found in _INVISIBLE.finditer(line):
        seen.setdefault(found.group(), found.start() + 1)
    if not seen:
        return None
    names = [
        f"U+{ord(char):04X} {unicodedata.name(char, 'UNNAMED')} at column {column}"
        for char, column in list(seen.items())[:3]
    ]
    if len(seen) > 3:
        names.append(f"and {len(seen) - 3} more")
    return ", ".join(names)


_DETECTORS: tuple[tuple[str, Callable[[str], str | None]], ...] = (
    (INJECTION, _first_match(_INJECTION)),
    (DOWNLOAD_EXEC, _first_match(_DOWNLOAD_EXEC)),
    (UPLOAD, _upload),
    (CREDENTIAL_REQUEST, _credential_request),
    (INVISIBLE, _invisible),
)


def suspicious_instructions(text: str) -> list[tuple[int, str, str]]:
    """`(línea, tipo, lo encontrado)` de cada instrucción sospechosa; una por tipo y línea.

    Revisa todas las líneas, también el frontmatter y los bloques de código.
    """
    found: list[tuple[int, str, str]] = []
    for number, line in enumerate(text.split("\n"), start=1):
        line = line.rstrip("\r")
        for kind, detect in _DETECTORS:
            excerpt = detect(line)
            if excerpt:
                found.append((number, kind, excerpt))
    return found


def instruction_message(kind: str, excerpt: str) -> str:
    why, action = _WHY[kind]
    return (
        f"suspicious instruction ({kind}): found {excerpt}; {why}. {action}. Review the skill "
        "with the skill-reviewer skill before installing or distributing it"
    )


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    message: str


@dataclass
class ValidationReport:
    errors: list[Finding] = field(default_factory=list)
    warnings: list[Finding] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass(frozen=True)
class _Ref:
    pack: str
    source: str
    line: int
    target: str


class _Validator:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.report = ValidationReport()
        self.packs: dict[str, Pack] = {}
        self.skills: dict[str, list[tuple[str, str]]] = {}
        self.refs: list[_Ref] = []
        self.subagents: dict[str, list[str]] = {}
        self.citations: list[tuple[Path, int, str, str]] = []
        self.shared: dict[str, set[str]] = {}
        self.shared_count = 0
        self.map = phase_map.load(self.root)

    def rel(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def error(self, path: Path, line: int, message: str) -> None:
        self.report.errors.append(Finding(self.rel(path), line, message))

    def warn(self, path: Path, line: int, message: str) -> None:
        self.report.warnings.append(Finding(self.rel(path), line, message))

    # -- packs --------------------------------------------------------------

    def check_packs(self) -> None:
        folder = self.root / "packs"
        if not folder.is_dir():
            self.error(self.root, 0, "missing packs/ folder")
            return
        for pack_dir in sorted(
            p for p in folder.iterdir() if p.is_dir() and not p.name.startswith("_")
        ):
            try:
                self.packs[pack_dir.name] = load_pack(pack_dir)
            except PackError as exc:
                self.error(pack_dir / MANIFEST, 0, str(exc))
        for name, pack in self.packs.items():
            for required in pack.requires:
                if required not in self.packs:
                    self.error(
                        pack.path / MANIFEST,
                        0,
                        f"requires {required!r}, which is not in the collection",
                    )
            try:
                resolve({k: v for k, v in self.packs.items()}, [name])
            except PackError as exc:
                if "cycle" in str(exc):
                    self.error(pack.path / MANIFEST, 0, str(exc))

    # -- skills -------------------------------------------------------------

    def check_skills(self) -> None:
        for pack in self.packs.values():
            skills_dir = pack.path / "skills"
            if not skills_dir.is_dir():
                continue
            for folder in sorted(skills_dir.iterdir()):
                if not folder.is_dir() or folder.name.startswith("_"):
                    continue
                if (folder / SKILL_FILE).is_file():
                    self.check_skill(pack, folder)
                else:
                    self.warn(folder, 0, f"skill folder without {SKILL_FILE}; it is not installed")
        for name, places in self.skills.items():
            if len(places) > 1:
                packs = ", ".join(p for p, _ in places)
                for _, path in places:
                    self.report.errors.append(
                        Finding(path, 0, f"duplicate skill name: {name} (packs {packs})")
                    )

    def check_skill(self, pack: Pack, folder: Path) -> None:
        path = folder / SKILL_FILE
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            self.error(path, 0, f"not valid UTF-8 ({exc.reason})")
            return
        self.check_instructions(path, text)
        self.check_body(path, text, folder, pack)
        references = folder / "references"
        if references.is_dir():
            for extra in fsutil.walk_files(references):
                if extra.suffix == ".md":
                    body = extra.read_text(encoding="utf-8")
                    self.check_body(extra, body, folder, pack)
                elif extra.suffix.lower() in _SCANNED | _SCRIPTS:
                    body = extra.read_text(encoding="utf-8", errors="replace")
                else:
                    continue
                self.check_instructions(extra, body)
        for extra in fsutil.walk_files(folder):
            if extra == path or extra.is_relative_to(references):
                continue
            if extra.suffix.lower() in _SCANNED | _SCRIPTS:
                self.check_instructions(extra, extra.read_text(encoding="utf-8", errors="replace"))
        try:
            data, _ = frontmatter.parse(text, strict=True)
        except frontmatter.FrontmatterError as exc:
            self.error(path, exc.line, f"invalid frontmatter: {exc.message}")
            return
        for key in data:
            if key not in STANDARD_FIELDS:
                self.error(
                    path,
                    0,
                    f"field {key!r} is not part of the Agent Skills standard; move it to "
                    "metadata with the engine prefix",
                )
        name = data.get("name")
        if not isinstance(name, str) or name != folder.name:
            self.error(path, 0, f"name must match the folder name ({folder.name!r}), not {name!r}")
        if isinstance(name, str):
            if not _NAME.match(name):
                self.error(
                    path, 0, f"name {name!r} must be kebab-case: a-z, 0-9 and single hyphens"
                )
            if len(name) > MAX_NAME:
                self.error(path, 0, f"name has {len(name)} characters; the maximum is {MAX_NAME}")
            self.skills.setdefault(name, []).append((pack.name, self.rel(path)))
        description = data.get("description")
        if not isinstance(description, str) or not description.strip():
            self.error(path, 0, "missing description (with triggers in English)")
        elif len(description) > MAX_DESCRIPTION:
            self.error(
                path,
                0,
                f"description has {len(description)} characters; the maximum is {MAX_DESCRIPTION}",
            )
        metadata = data.get("metadata", {})
        if not isinstance(metadata, dict):
            self.error(path, 0, "metadata must be a mapping of strings to strings")
        else:
            for key, value in metadata.items():
                if not isinstance(value, str):
                    self.error(path, 0, f"metadata.{key} must be a string, not {value!r}")
        compatibility = data.get("compatibility")
        if compatibility is not None and (
            not isinstance(compatibility, str) or len(compatibility) > MAX_COMPATIBILITY
        ):
            self.error(
                path,
                0,
                f"compatibility must be a string of up to {MAX_COMPATIBILITY} characters",
            )
        lines = len(text.splitlines())
        if lines > MAX_SKILL_LINES:
            self.warn(
                path,
                0,
                f"SKILL.md has {lines} lines, more than {MAX_SKILL_LINES} lines; "
                "move the details to references/",
            )

    def check_body(self, path: Path, text: str, folder: Path, pack: Pack) -> None:
        in_code = False
        for number, line in enumerate(text.splitlines(), start=1):
            if _FENCE.match(line):
                in_code = not in_code
                continue
            if in_code:
                continue
            for escape in _ESCAPE.findall(line):
                self.error(
                    path,
                    number,
                    f"literal Unicode escape {escape}: write the character directly",
                )
            for target in _SKILL_REF.findall(line):
                self.refs.append(_Ref(pack.name, self.rel(path), number, target))
            for cited in _REFERENCE_FILE.findall(line):
                cited = cited.rstrip(".,;:")
                if not (folder / cited).is_file():
                    self.error(path, number, f"cites {cited}, which does not exist")
            for cited in _SHARED_PATH.findall(line):
                self.citations.append((path, number, cited.rstrip(".,;:"), pack.name))

    def check_instructions(self, path: Path, text: str) -> None:
        """Pre-chequeo de instrucciones sospechosas: advierte, nunca da error."""
        for number, kind, excerpt in suspicious_instructions(text):
            self.warn(path, number, instruction_message(kind, excerpt))

    # -- contratos compartidos ------------------------------------------------

    def check_shared(self) -> None:
        engine = self.shared.setdefault(ENGINE_SHARED_PACK, set())
        for folder_name, source, pattern in ENGINE_SHARED:
            engine.update(f"{folder_name}/{p.name}" for p in source.glob(pattern))
        for pack in self.packs.values():
            folder = pack.path / SHARED_DIR
            if not folder.is_dir():
                continue
            for path in fsutil.walk_files(folder):
                rel = path.relative_to(folder).as_posix()
                self.shared.setdefault(pack.name, set()).add(rel)
                self.shared_count += 1
                if path.suffix == ".json":
                    self.check_json(path, rel)
                elif path.suffix == ".md":
                    self.check_body(path, path.read_text(encoding="utf-8"), path.parent, pack)

    def check_json(self, path: Path, rel: str) -> None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self.error(path, 0, f"not valid JSON ({exc})")
            return
        if rel.startswith("schemas/"):
            try:
                jsonschema.check_schema(data)
            except jsonschema.SchemaError as exc:
                self.error(path, 0, f"schema not supported by the engine validator: {exc}")

    def _reachable(self, pack: str) -> set[str]:
        """El pack y lo que requiere: lo que seguro está instalado junto con él."""
        try:
            names = resolve(self.packs, [pack])
        except PackError:
            names = [pack]
        found: set[str] = set()
        for name in names:
            found |= self.shared.get(name, set())
        return found

    @staticmethod
    def _has(files: set[str], cited: str) -> bool:
        return cited in files or (cited.endswith("/") and any(f.startswith(cited) for f in files))

    def check_citations(self) -> None:
        prefix = f"{_meta.PROJECT_DIR}/shared/"
        for path, number, cited, pack in self.citations:
            if self._has(self._reachable(pack), cited):
                continue
            owners = sorted(name for name, files in self.shared.items() if self._has(files, cited))
            if owners:
                message = (
                    f"cites {prefix}{cited}, which ships in pack {', '.join(owners)}; pack {pack} "
                    "does not require it, so it is missing when only that pack is installed"
                )
            else:
                message = f"cites {prefix}{cited}, which does not exist in any shared/ folder"
            self.error(path, number, message)

    def check_refs(self) -> None:
        for ref in self.refs:
            pack = self.packs[ref.pack]
            places = self.skills.get(ref.target)
            if places:
                owner = places[0][0]
                if owner != ref.pack and owner not in pack.requires + pack.optional:
                    self.report.errors.append(
                        Finding(
                            ref.source,
                            ref.line,
                            f"skill:{ref.target} belongs to pack {owner}, which "
                            f"{ref.pack} does not declare in requires or optional",
                        )
                    )
                continue
            declared = self.map.degradations.get(ref.target) if self.map else None
            if declared is None:
                self.report.errors.append(
                    Finding(
                        ref.source,
                        ref.line,
                        f"skill:{ref.target} is not in the collection; if it ships in a "
                        f"later pack, declare it in {phase_map.MAP_FILE} "
                        f"({phase_map.DEGRADATIONS_SECTION})",
                    )
                )
            elif declared.pack not in (ref.pack, *pack.requires, *pack.optional):
                self.report.errors.append(
                    Finding(
                        ref.source,
                        ref.line,
                        f"skill:{ref.target} degrades to pack {declared.pack}, which {ref.pack} "
                        "does not declare in requires or optional",
                    )
                )

    # -- subagentes, reglas y secretos --------------------------------------

    def check_subagents(self) -> None:
        for pack in self.packs.values():
            agents = pack.path / "agents"
            for path in sorted(agents.glob("*.md")) if agents.is_dir() else []:
                try:
                    text = path.read_text(encoding="utf-8")
                except UnicodeDecodeError as exc:
                    self.error(path, 0, f"not valid UTF-8 ({exc.reason})")
                    continue
                self.check_instructions(path, text)
                try:
                    data, _ = frontmatter.parse(text, strict=True)
                except frontmatter.FrontmatterError as exc:
                    self.error(path, exc.line, f"invalid frontmatter: {exc.message}")
                    continue
                name = data.get("name")
                if not isinstance(name, str) or not name:
                    self.error(path, 0, "subagent is missing name")
                    continue
                if not isinstance(data.get("description"), str) or not data["description"].strip():
                    self.error(path, 0, "subagent is missing description")
                self.check_subagent_shell(path, data.get("tools"))
                self.subagents.setdefault(name, []).append(self.rel(path))
        for name, paths in self.subagents.items():
            if len(paths) > 1:
                for rel in paths:
                    self.report.errors.append(Finding(rel, 0, f"duplicate subagent: {name}"))

    def check_subagent_shell(self, path: Path, tools: object) -> None:
        """Un subagente con shell la declara para los dos agentes que leen `.claude/agents/`.

        Claude Code usa `Bash` (y `PowerShell` en Windows); GitHub Copilot CLI 1.0.114 en
        Windows no le da shell a un subagente que declara solo `Bash`, aunque su
        documentación lo trate como alias (verificado en F8). Con `PowerShell`, sí.
        """
        if isinstance(tools, str):
            names = tools.split(",")
        elif isinstance(tools, list):
            names = [str(t) for t in tools]
        else:
            return
        lowered = {name.strip().lower() for name in names}
        if "bash" in lowered and "powershell" not in lowered:
            self.error(
                path,
                0,
                "tools lists Bash but not PowerShell: GitHub Copilot CLI on Windows gives a "
                "subagent no shell with Bash alone; add PowerShell",
            )

    def check_rules(self) -> None:
        path = self.root / RULES_FILE
        if not path.is_file():
            self.error(self.root, 0, f"missing {RULES_FILE.as_posix()}")
            return
        lines = len(path.read_text(encoding="utf-8").splitlines())
        if lines > MAX_RULE_LINES:
            self.error(path, 0, f"AGENTS.base.md exceeds {MAX_RULE_LINES} lines (has {lines})")

    def check_secrets(self) -> None:
        for path in sorted(self.root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in _SCANNED:
                continue
            for finding in secrets.scan_text(path.read_text(encoding="utf-8", errors="replace")):
                self.error(
                    path, finding.line, f"possible secret ({finding.kind}): {finding.excerpt}"
                )

    def run(self) -> ValidationReport:
        self.check_packs()
        self.check_shared()
        self.check_skills()
        self.check_refs()
        self.check_citations()
        self.check_subagents()
        self.check_rules()
        self.check_secrets()
        self.report.counts = {
            "packs": len(self.packs),
            "skills": sum(len(v) for v in self.skills.values()),
            "subagents": sum(len(v) for v in self.subagents.values()),
            "shared": self.shared_count,
        }
        return self.report


def validate(root: Path) -> ValidationReport:
    return _Validator(root).run()
