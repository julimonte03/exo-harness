"""R1, estructura: módulos y grafo de imports (F6, ADR-0015, D-14).

**Módulo:** la carpeta que contiene archivos de código de producción (ni tests ni
migraciones). **Arista:** un import de un archivo de la carpeta A que resuelve a un
archivo del proyecto en la carpeta B, con A distinta de B. Los imports a paquetes
externos son dependencias, no aristas.

Los extractores son heurísticos con stdlib (D-14):
- **Python:** `ast` sobre los bytes, y regex si no parsea.
- **JS/TS:** regex sobre el texto sin comentarios, con extensiones, `index`, los
  `paths` del `tsconfig.json` y los workspaces del repo.
- **Java:** regex de `import`, con las raíces `src/main/java/`.

Un archivo que no es UTF-8 se lee con caracteres de reemplazo y queda en `warnings`.
"""

from __future__ import annotations

import ast
import json
import posixpath
import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from exo.discovery import files as files_mod
from exo.discovery import store

FILENAME = "structure.json"
MERMAID = "module-graph.mmd"
JS_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
_PY_FALLBACK = re.compile(
    r"^\s*(?:from\s+(\.*[\w.]*)\s+import\s+(.+)|import\s+(.+))$", re.MULTILINE
)
_JS_SPECIFIERS = (
    re.compile(r"\bimport\s+(?:[\w*{}\s,$]+?\s+from\s+)?(['\"`])([^'\"`$]+)\1"),
    re.compile(r"\bexport\s+(?:[\w*{}\s,$]+?)\s+from\s+(['\"`])([^'\"`$]+)\1"),
    re.compile(r"\bimport\s*\(\s*(['\"`])([^'\"`$]+)\1\s*\)"),
    re.compile(r"\brequire\s*\(\s*(['\"`])([^'\"`$]+)\1\s*\)"),
)
_JAVA_IMPORT = re.compile(r"^\s*import\s+(static\s+)?([\w.]+?)(\.\*)?\s*;", re.MULTILINE)


@dataclass
class Index:
    """Lo que necesitan los extractores para resolver: archivos, carpetas y configuración."""

    files: set[str]
    dirs: set[str] = field(default_factory=set)
    python_roots: list[str] = field(default_factory=list)
    java_roots: list[str] = field(default_factory=list)
    workspaces: dict[str, tuple[str, str | None]] = field(
        default_factory=dict
    )  # nombre -> (dir, main)
    tsconfigs: dict[str, tuple[str, dict[str, list[str]]]] = field(default_factory=dict)

    @classmethod
    def build(
        cls, project: Path, paths: list[str], reader: files_mod.TextReader | None = None
    ) -> Index:
        reader = reader or files_mod.TextReader(project)
        index = cls(set(paths))
        for path in paths:
            parent = PurePosixPath(path).parent
            while True:
                index.dirs.add(parent.as_posix())
                if parent == parent.parent:
                    break
                parent = parent.parent
        roots = {"."}
        for path in paths:
            name = PurePosixPath(path).name
            folder = posixpath.dirname(path) or "."
            if name in ("pyproject.toml", "setup.py", "setup.cfg"):
                roots.add(folder)
        index.python_roots = sorted(
            {_join(r, "src") for r in roots if _join(r, "src") in index.dirs} | roots,
            key=lambda r: (-len(r), r),
        )
        index.java_roots = sorted(
            {d for d in index.dirs if d == "src/main/java" or d.endswith("/src/main/java")}
        )
        index.workspaces = _workspaces(reader, paths)
        index.tsconfigs = _tsconfigs(reader, paths)
        return index


def _join(*parts: str) -> str:
    joined = posixpath.normpath(posixpath.join(*[p for p in parts if p and p != "."]) or ".")
    return joined


# -- Python ---------------------------------------------------------------------------------


def _py_module_file(base: str, dotted: str, index: Index) -> str | None:
    parts = [p for p in dotted.split(".") if p]
    if not parts:
        candidate = _join(base, "__init__.py")
        return candidate if candidate in index.files else None
    stem = _join(base, *parts)
    for candidate in (stem + ".py", _join(stem, "__init__.py")):
        if candidate in index.files:
            return candidate
    return None


def _py_from(base: str, module: str, names: list[str], index: Index) -> set[str]:
    """`from <module> import <names>` desde `base`: cada nombre que es un submódulo, o el
    módulo mismo si ninguno lo es (los nombres son funciones o clases del módulo)."""
    found: set[str] = set()
    for name in names:
        if name != "*":
            target = _py_module_file(base, f"{module}.{name}" if module else name, index)
            if target:
                found.add(target)
    if found:
        return found
    target = _py_module_file(base, module, index)
    return {target} if target else set()


def _py_resolve_absolute(dotted: str, names: list[str], index: Index) -> set[str]:
    for root in index.python_roots:
        found = _py_from(root, dotted, names, index)
        if found:
            return found
    return set()


def python_imports(path: str, source: bytes, index: Index) -> tuple[set[str], set[str]]:
    """(archivos del proyecto importados, paquetes externos) de un archivo Python."""
    resolved: set[str] = set()
    external: set[str] = set()
    package = posixpath.dirname(path) or "."
    try:
        # Un escape inválido en un string del proyecto da un SyntaxWarning: no es nuestro.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            tree = ast.parse(source)
        statements: list[tuple[int, str, list[str]]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                statements += [(0, alias.name, []) for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [alias.name for alias in node.names]
                statements.append((node.level, node.module or "", names))
    except (SyntaxError, ValueError):
        statements = []
        text = files_mod.decode(files_mod.to_lf(source))[0]
        for match in _PY_FALLBACK.finditer(text):
            if match.group(3):
                for item in match.group(3).split(","):
                    statements.append((0, item.split(" as ")[0].strip(), []))
            else:
                module = match.group(1)
                level = len(module) - len(module.lstrip("."))
                names = [n.split(" as ")[0].strip(" \t()") for n in match.group(2).split(",")]
                statements.append((level, module.lstrip("."), names))
    for level, module, names in statements:
        if level:
            base = package
            for _ in range(level - 1):
                base = posixpath.dirname(base) or "."
            resolved |= _py_from(base, module, names, index)
            continue
        found = _py_resolve_absolute(module, names, index)
        if found:
            resolved |= found
        elif module:
            external.add(module.split(".")[0])
    return resolved, external


# -- JS/TS ----------------------------------------------------------------------------------


def strip_comments(text: str) -> str:
    """El texto sin comentarios `//` y `/* */`, respetando strings y template literals."""
    out: list[str] = []
    index, size = 0, len(text)
    quote: str | None = None
    while index < size:
        char = text[index]
        if quote:
            out.append(char)
            if char == "\\" and index + 1 < size:
                out.append(text[index + 1])
                index += 2
                continue
            if char == quote:
                quote = None
            index += 1
            continue
        if char in "'\"`":
            quote = char
            out.append(char)
            index += 1
            continue
        if text.startswith("//", index):
            end = text.find("\n", index)
            index = size if end < 0 else end
            continue
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            stop = size if end < 0 else end + 2
            out.append("\n" * text.count("\n", index, stop))
            index = stop
            continue
        out.append(char)
        index += 1
    return "".join(out)


def _loose_json(text: str) -> Any:
    """JSON con comentarios y comas finales, como el de un `tsconfig.json`."""
    clean = re.sub(r",(\s*[}\]])", r"\1", strip_comments(text))
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        return None


def _workspaces(
    reader: files_mod.TextReader, paths: list[str]
) -> dict[str, tuple[str, str | None]]:
    """Paquetes del propio repo, por nombre: (carpeta, archivo de entrada)."""
    root = _loose_json(reader.text("package.json")) if "package.json" in paths else None
    patterns: list[str] = []
    if isinstance(root, dict):
        spaces = root.get("workspaces")
        if isinstance(spaces, dict):
            spaces = spaces.get("packages")
        if isinstance(spaces, list):
            patterns = [str(p).rstrip("/") for p in spaces]
    found: dict[str, tuple[str, str | None]] = {}
    for path in paths:
        if PurePosixPath(path).name != "package.json" or path == "package.json":
            continue
        folder = posixpath.dirname(path)
        if patterns and not any(PurePosixPath(folder).match(p) for p in patterns):
            continue
        data = _loose_json(reader.text(path))
        if not isinstance(data, dict) or not isinstance(data.get("name"), str):
            continue
        entry = data.get("main")
        exports = data.get("exports")
        if isinstance(exports, dict) and isinstance(exports.get("."), str):
            entry = exports["."]
        elif isinstance(exports, str):
            entry = exports
        found[data["name"]] = (folder, entry if isinstance(entry, str) else None)
    return found


def _tsconfigs(
    reader: files_mod.TextReader, paths: list[str]
) -> dict[str, tuple[str, dict[str, list[str]]]]:
    """Por carpeta de cada `tsconfig.json`: (baseUrl resuelto, paths)."""
    found: dict[str, tuple[str, dict[str, list[str]]]] = {}
    for path in paths:
        if PurePosixPath(path).name != "tsconfig.json":
            continue
        folder = posixpath.dirname(path) or "."
        data = _loose_json(reader.text(path))
        options = data.get("compilerOptions") if isinstance(data, dict) else None
        if not isinstance(options, dict):
            continue
        base = _join(folder, str(options.get("baseUrl", ".")))
        aliases = options.get("paths")
        clean = {
            str(k): [str(v) for v in values]
            for k, values in (aliases.items() if isinstance(aliases, dict) else [])
            if isinstance(values, list)
        }
        found[folder] = (base, clean)
    return found


def _js_file(stem: str, index: Index) -> str | None:
    candidates = [stem] + [stem + ext for ext in JS_EXTENSIONS]
    candidates += [_join(stem, "index" + ext) for ext in JS_EXTENSIONS]
    for candidate in candidates:
        if candidate in index.files:
            return candidate
    return None


def _nearest_tsconfig(path: str, index: Index) -> tuple[str, dict[str, list[str]]] | None:
    folder = PurePosixPath(path).parent
    while True:
        key = folder.as_posix()
        if key in index.tsconfigs:
            return index.tsconfigs[key]
        if folder == folder.parent:
            return None
        folder = folder.parent


def _js_resolve(path: str, spec: str, index: Index) -> tuple[str | None, str | None]:
    """(archivo resuelto, paquete externo) de un especificador."""
    if spec.startswith((".", "/")):
        return _js_file(_join(posixpath.dirname(path) or ".", spec), index), None
    config = _nearest_tsconfig(path, index)
    if config:
        base, aliases = config
        for pattern, targets in aliases.items():
            prefix, star, suffix = pattern.partition("*")
            if star and spec.startswith(prefix) and spec.endswith(suffix):
                middle = spec[len(prefix) : len(spec) - len(suffix) if suffix else None]
                for target in targets:
                    found = _js_file(_join(base, target.replace("*", middle, 1)), index)
                    if found:
                        return found, None
            elif not star and spec == pattern:
                for target in targets:
                    found = _js_file(_join(base, target), index)
                    if found:
                        return found, None
    for name, (folder, entry) in index.workspaces.items():
        if spec == name:
            found = _js_file(_join(folder, entry or "index"), index)
            return found, None if found else name
        if spec.startswith(name + "/"):
            return _js_file(_join(folder, spec[len(name) + 1 :]), index), None
    parts = spec.split("/")
    package = "/".join(parts[:2]) if spec.startswith("@") else parts[0]
    return None, package


def js_imports(path: str, text: str, index: Index) -> tuple[set[str], set[str]]:
    resolved: set[str] = set()
    external: set[str] = set()
    clean = strip_comments(text)
    for pattern in _JS_SPECIFIERS:
        for match in pattern.finditer(clean):
            found, package = _js_resolve(path, match.group(2), index)
            if found:
                resolved.add(found)
            elif package and not match.group(2).startswith((".", "/")):
                external.add(package)
    return resolved, external


# -- Java -----------------------------------------------------------------------------------


def java_imports(path: str, text: str, index: Index) -> tuple[set[str], set[str]]:
    resolved: set[str] = set()
    external: set[str] = set()
    for match in _JAVA_IMPORT.finditer(strip_comments(text)):
        static, dotted, wildcard = match.groups()
        parts = dotted.split(".")
        if static and not wildcard:
            parts = parts[:-1]  # import static a.b.C.m: la clase es a.b.C
        found = None
        for root in index.java_roots:
            if wildcard and not static:
                folder = _join(root, *parts)
                if folder in index.dirs:
                    found = next(
                        (f for f in sorted(index.files) if posixpath.dirname(f) == folder), None
                    )
            else:
                candidate = _join(root, *parts) + ".java"
                if candidate in index.files:
                    found = candidate
            if found:
                break
        if found:
            resolved.add(found)
        else:
            external.add(".".join(parts[: min(3, len(parts))]))
    return resolved, external


# -- estructura -----------------------------------------------------------------------------


def module_of(path: str) -> str:
    return posixpath.dirname(path) or "."


def imports(
    item: files_mod.SourceFile, index: Index, reader: files_mod.TextReader
) -> tuple[set[str], set[str]]:
    """(archivos del proyecto importados, paquetes externos) de un archivo, por lenguaje."""
    if item.language == "python":
        return python_imports(item.path, reader.python(item.path), index)
    if item.language in ("javascript", "typescript"):
        return js_imports(item.path, reader.text(item.path), index)
    if item.language == "java":
        return java_imports(item.path, reader.text(item.path), index)
    return set(), set()


def build(project: Path, fileset: files_mod.FileSet | None = None) -> dict[str, Any]:
    project = Path(project)
    fileset = fileset or files_mod.list_files(project)
    readable = [f.path for f in fileset.files if not f.sensitive]
    reader = files_mod.TextReader(project)
    index = Index.build(project, readable, reader)
    code = [f for f in fileset.files if f.category == "code"]
    modules: dict[str, dict[str, Any]] = {}
    edges: dict[tuple[str, str], int] = {}
    external: dict[str, set[str]] = {}
    production = {f.path for f in code}
    for item in code:
        module = module_of(item.path)
        entry = modules.setdefault(module, {"files": 0, "lines": 0, "languages": set()})
        entry["files"] += 1
        entry["lines"] += item.lines
        if item.language:
            entry["languages"].add(item.language)
        targets, outside = imports(item, index, reader)
        external.setdefault(module, set()).update(outside)
        for target in targets:
            if target not in production:
                continue
            other = module_of(target)
            if other != module:
                edges[(module, other)] = edges.get((module, other), 0) + 1
    fan_in = {m: len({a for a, b in edges if b == m}) for m in modules}
    fan_out = {m: len({b for a, b in edges if a == m}) for m in modules}
    return {
        "modules": [
            {
                "path": name,
                "files": data["files"],
                "lines": data["lines"],
                "languages": sorted(data["languages"]),
                "fan_in": fan_in[name],
                "fan_out": fan_out[name],
                "external": sorted(external.get(name, set())),
            }
            for name, data in sorted(modules.items())
        ],
        "edges": [{"from": a, "to": b, "imports": n} for (a, b), n in sorted(edges.items())],
        "warnings": reader.warnings,
    }


def mermaid(structure: dict[str, Any]) -> str:
    ids = {m["path"]: f"m{i}" for i, m in enumerate(structure["modules"], start=1)}
    lines = ["graph LR"]
    lines += [f'  {ids[m["path"]]}["{m["path"]}"]' for m in structure["modules"]]
    lines += [f"  {ids[e['from']]} --> {ids[e['to']]}" for e in structure["edges"]]
    return "\n".join(lines) + "\n"


def write(project: Path, fileset: files_mod.FileSet | None = None) -> tuple[dict[str, Any], bool]:
    data = build(project, fileset)
    wrote = store.write_json(project, FILENAME, data)
    wrote = store.write_text(project, MERMAID, mermaid(data)) or wrote
    return data, wrote
