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
  Si no resuelven pero el pack declara opcionales ausentes de la colección, es
  advertencia: la skill degrada inline.
- Subagentes con `name` y `description`, sin repetir.
- `rules/AGENTS.base.md` de hasta 60 líneas.
- Sin patrones de secretos fuera de bloques de código.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from exo.core import frontmatter, secrets
from exo.packs import MANIFEST, SKILL_FILE, Pack, PackError, load_pack, resolve

STANDARD_FIELDS = ("name", "description", "license", "compatibility", "metadata", "allowed-tools")
MAX_NAME = 64
MAX_DESCRIPTION = 1024
MAX_COMPATIBILITY = 500
MAX_SKILL_LINES = 500
MAX_RULE_LINES = 60
RULES_FILE = Path("rules") / "AGENTS.base.md"
_SCANNED = {".md", ".json", ".txt", ".yml", ".yaml", ".toml"}
_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_ESCAPE = re.compile(r"\\u[0-9a-fA-F]{4}")
_SKILL_REF = re.compile(r"\bskill:([a-z0-9][a-z0-9-]*)")
# Rutas relativas a la skill; no cuenta dentro de URLs ni de otras rutas (x/references/...).
_REFERENCE_FILE = re.compile(r"(?<![\w/.:-])references/[^\s)\]'\"`<>]+")
_FENCE = re.compile(r"^\s*(```|~~~)")


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
            self.error(self.root, 0, "falta la carpeta packs/")
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
                        f"requires {required!r}, que no existe en la colección",
                    )
            try:
                resolve({k: v for k, v in self.packs.items()}, [name])
            except PackError as exc:
                if "ciclo" in str(exc):
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
                    self.warn(folder, 0, f"carpeta de skill sin {SKILL_FILE}; no se instala")
        for name, places in self.skills.items():
            if len(places) > 1:
                packs = ", ".join(p for p, _ in places)
                for _, path in places:
                    self.report.errors.append(
                        Finding(path, 0, f"nombre de skill repetido: {name} (packs {packs})")
                    )

    def check_skill(self, pack: Pack, folder: Path) -> None:
        path = folder / SKILL_FILE
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            self.error(path, 0, f"no es UTF-8 válido ({exc.reason})")
            return
        self.check_body(path, text, folder, pack)
        try:
            data, _ = frontmatter.parse(text, strict=True)
        except frontmatter.FrontmatterError as exc:
            self.error(path, exc.line, f"frontmatter inválido: {exc.message}")
            return
        for key in data:
            if key not in STANDARD_FIELDS:
                self.error(
                    path,
                    0,
                    f"el campo {key!r} no es del estándar Agent Skills; movelo a metadata con "
                    "prefijo del motor",
                )
        name = data.get("name")
        if not isinstance(name, str) or name != folder.name:
            self.error(
                path, 0, f"name tiene que ser igual a la carpeta ({folder.name!r}), no {name!r}"
            )
        if isinstance(name, str):
            if not _NAME.match(name):
                self.error(
                    path, 0, f"name {name!r} tiene que ser kebab-case: a-z, 0-9 y guiones simples"
                )
            if len(name) > MAX_NAME:
                self.error(path, 0, f"name tiene {len(name)} caracteres; el máximo es {MAX_NAME}")
            self.skills.setdefault(name, []).append((pack.name, self.rel(path)))
        description = data.get("description")
        if not isinstance(description, str) or not description.strip():
            self.error(path, 0, "falta description (con disparadores en español e inglés)")
        elif len(description) > MAX_DESCRIPTION:
            self.error(
                path,
                0,
                f"description tiene {len(description)} caracteres; el máximo es {MAX_DESCRIPTION}",
            )
        metadata = data.get("metadata", {})
        if not isinstance(metadata, dict):
            self.error(path, 0, "metadata tiene que ser un mapa de texto a texto")
        else:
            for key, value in metadata.items():
                if not isinstance(value, str):
                    self.error(path, 0, f"metadata.{key} tiene que ser texto, no {value!r}")
        compatibility = data.get("compatibility")
        if compatibility is not None and (
            not isinstance(compatibility, str) or len(compatibility) > MAX_COMPATIBILITY
        ):
            self.error(
                path,
                0,
                f"compatibility tiene que ser texto de hasta {MAX_COMPATIBILITY} caracteres",
            )
        lines = len(text.splitlines())
        if lines > MAX_SKILL_LINES:
            self.warn(
                path,
                0,
                f"SKILL.md tiene {lines} líneas, más de {MAX_SKILL_LINES} líneas; "
                "pasá el detalle a references/",
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
                    f"escape Unicode literal {escape}: escribí el carácter directamente",
                )
            for target in _SKILL_REF.findall(line):
                self.refs.append(_Ref(pack.name, self.rel(path), number, target))
            for cited in _REFERENCE_FILE.findall(line):
                cited = cited.rstrip(".,;:")
                if not (folder / cited).is_file():
                    self.error(path, number, f"cita {cited}, que no existe")

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
                            f"skill:{ref.target} es del pack {owner}, que "
                            f"{ref.pack} no declara en requires ni optional",
                        )
                    )
                continue
            absent = [p for p in pack.optional if p not in self.packs]
            if absent:
                self.report.warnings.append(
                    Finding(
                        ref.source,
                        ref.line,
                        f"skill:{ref.target} no se puede resolver: los packs "
                        f"opcionales {', '.join(absent)} no están en la colección (degrada inline)",
                    )
                )
            else:
                self.report.errors.append(
                    Finding(ref.source, ref.line, f"skill:{ref.target} no existe en la colección")
                )

    # -- subagentes, reglas y secretos --------------------------------------

    def check_subagents(self) -> None:
        for pack in self.packs.values():
            agents = pack.path / "agents"
            for path in sorted(agents.glob("*.md")) if agents.is_dir() else []:
                try:
                    data, _ = frontmatter.parse(path.read_text(encoding="utf-8"), strict=True)
                except frontmatter.FrontmatterError as exc:
                    self.error(path, exc.line, f"frontmatter inválido: {exc.message}")
                    continue
                except UnicodeDecodeError as exc:
                    self.error(path, 0, f"no es UTF-8 válido ({exc.reason})")
                    continue
                name = data.get("name")
                if not isinstance(name, str) or not name:
                    self.error(path, 0, "falta name en el subagente")
                    continue
                if not isinstance(data.get("description"), str) or not data["description"].strip():
                    self.error(path, 0, "falta description en el subagente")
                self.subagents.setdefault(name, []).append(self.rel(path))
        for name, paths in self.subagents.items():
            if len(paths) > 1:
                for rel in paths:
                    self.report.errors.append(Finding(rel, 0, f"subagente repetido: {name}"))

    def check_rules(self) -> None:
        path = self.root / RULES_FILE
        if not path.is_file():
            self.error(self.root, 0, f"falta {RULES_FILE.as_posix()}")
            return
        lines = len(path.read_text(encoding="utf-8").splitlines())
        if lines > MAX_RULE_LINES:
            self.error(path, 0, f"AGENTS.base.md supera {MAX_RULE_LINES} líneas (tiene {lines})")

    def check_secrets(self) -> None:
        for path in sorted(self.root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in _SCANNED:
                continue
            for finding in secrets.scan_text(path.read_text(encoding="utf-8", errors="replace")):
                self.error(
                    path, finding.line, f"posible secreto ({finding.kind}): {finding.excerpt}"
                )

    def run(self) -> ValidationReport:
        self.check_packs()
        self.check_skills()
        self.check_refs()
        self.check_subagents()
        self.check_rules()
        self.check_secrets()
        self.report.counts = {
            "packs": len(self.packs),
            "skills": sum(len(v) for v in self.skills.values()),
            "subagents": sum(len(v) for v in self.subagents.values()),
        }
        return self.report


def validate(root: Path) -> ValidationReport:
    return _Validator(root).run()
