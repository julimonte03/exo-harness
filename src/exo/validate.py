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
"""

from __future__ import annotations

import json
import re
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
_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_ESCAPE = re.compile(r"\\u[0-9a-fA-F]{4}")
_SKILL_REF = re.compile(r"\bskill:([a-z0-9][a-z0-9-]*)")
# Rutas relativas a la skill; no cuenta dentro de URLs ni de otras rutas (x/references/...).
_REFERENCE_FILE = re.compile(r"(?<![\w/.:-])references/[^\s)\]'\"`<>]+")
_FENCE = re.compile(r"^\s*(```|~~~)")
SHARED_DIR = "shared"
_SHARED_PATH = re.compile(rf"{re.escape(_meta.PROJECT_DIR)}/shared/([A-Za-z0-9._/-]+)")


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
        self.check_body(path, text, folder, pack)
        references = folder / "references"
        if references.is_dir():
            for extra in fsutil.walk_files(references):
                if extra.suffix == ".md":
                    self.check_body(extra, extra.read_text(encoding="utf-8"), folder, pack)
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
            self.error(
                path, 0, f"name must match the folder name ({folder.name!r}), not {name!r}"
            )
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
                    data, _ = frontmatter.parse(path.read_text(encoding="utf-8"), strict=True)
                except frontmatter.FrontmatterError as exc:
                    self.error(path, exc.line, f"invalid frontmatter: {exc.message}")
                    continue
                except UnicodeDecodeError as exc:
                    self.error(path, 0, f"not valid UTF-8 ({exc.reason})")
                    continue
                name = data.get("name")
                if not isinstance(name, str) or not name:
                    self.error(path, 0, "subagent is missing name")
                    continue
                if not isinstance(data.get("description"), str) or not data["description"].strip():
                    self.error(path, 0, "subagent is missing description")
                self.subagents.setdefault(name, []).append(self.rel(path))
        for name, paths in self.subagents.items():
            if len(paths) > 1:
                for rel in paths:
                    self.report.errors.append(Finding(rel, 0, f"duplicate subagent: {name}"))

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
