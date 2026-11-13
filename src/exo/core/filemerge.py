"""Bloques marcados dentro de archivos que también edita el humano.

Un bloque va entre marcadores `BEGIN:<prefijo>:<id>` y `END:<prefijo>:<id>`,
como comentario HTML (`<!-- … -->`) en Markdown/HTML o con `#` en TOML, YAML,
shell y similares. Lo que está fuera de los bloques es del humano y no se toca.

- Idempotente: si el resultado es igual al archivo actual, no se escribe.
- Conserva los fines de línea (CRLF o LF) y el BOM del archivo.
- `inject` y luego `remove` dejan el archivo como estaba, si terminaba en salto de línea.
- Backup opt-in (`backup=True`) a `<archivo>.<NAME>.bak`; el motor de
  operaciones de F2 usa snapshots en lugar de esto (invariante 11).
- Marcadores rotos (BEGIN sin END, ids repetidos, bloques anidados) son
  `BlockError` y el archivo no se modifica.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from exo import _meta
from exo.core import fsutil

STYLE_HTML = "html"
STYLE_HASH = "hash"

_HTML_SUFFIXES = {".md", ".markdown", ".mdc", ".html", ".htm", ".xml"}
_HASH_SUFFIXES = {".toml", ".yaml", ".yml", ".sh", ".bash", ".ps1", ".py", ".cfg", ".ini", ".conf"}
_HASH_NAMES = {".gitignore", ".gitattributes", ".editorconfig", "CODEOWNERS"}
_ID = re.compile(r"^[a-z0-9]+(?:[-_.][a-z0-9]+)*$")
_PREFIX = re.escape(_meta.BLOCK_PREFIX)
_MARKER = {
    STYLE_HTML: re.compile(rf"^\s*<!-- (BEGIN|END):{_PREFIX}:(\S+) -->\s*$"),
    STYLE_HASH: re.compile(rf"^\s*# (BEGIN|END):{_PREFIX}:(\S+)\s*$"),
}


class BlockError(ValueError):
    """El archivo tiene marcadores inválidos o la operación no se puede hacer."""


@dataclass(frozen=True)
class Block:
    id: str
    start_line: int  # 1-based, línea del BEGIN
    end_line: int  # 1-based, línea del END
    content: str


def style_for(path: Path) -> str:
    path = Path(path)
    if path.name in _HASH_NAMES or path.suffix.lower() in _HASH_SUFFIXES:
        return STYLE_HASH
    if path.suffix.lower() in _HTML_SUFFIXES:
        return STYLE_HTML
    raise BlockError(f"unknown comment style for {path.name}; pass style='html' or 'hash'")


def markers(block_id: str, style: str) -> tuple[str, str]:
    _check_id(block_id)
    tag = _meta.BLOCK_PREFIX
    if style == STYLE_HTML:
        return f"<!-- BEGIN:{tag}:{block_id} -->", f"<!-- END:{tag}:{block_id} -->"
    if style == STYLE_HASH:
        return f"# BEGIN:{tag}:{block_id}", f"# END:{tag}:{block_id}"
    raise BlockError(f"unknown style: {style!r}")


def _check_id(block_id: str) -> None:
    if not _ID.match(block_id):
        raise BlockError(
            f"invalid block id: {block_id!r} (lowercase letters, digits and separators - _ .)"
        )


# -- operaciones sobre texto ------------------------------------------------


def _newline(text: str) -> str:
    crlf = text.count("\r\n")
    return "\r\n" if crlf and crlf >= text.count("\n") - crlf else "\n"


# Solo \r\n y \n separan líneas: \r suelto, \f, \x85 o U+2028 son contenido del humano.
_LINE_BREAK = re.compile(r"(\r\n|\n)")
_FENCE = re.compile(r"^\s*(```|~~~)")

Line = list[str]  # [texto, separador]; el separador es "\r\n", "\n" o "" (última línea)


def _split(text: str) -> tuple[str, list[Line]]:
    """Devuelve (BOM, líneas con su separador original)."""
    bom = "\ufeff" if text.startswith("\ufeff") else ""
    body = text[len(bom) :]
    if not body:
        return bom, []
    parts = _LINE_BREAK.split(body)
    lines = [[parts[i], parts[i + 1]] for i in range(0, len(parts) - 1, 2)]
    if parts[-1]:
        lines.append([parts[-1], ""])
    return bom, lines


def _join(bom: str, lines: list[Line]) -> str:
    return bom + "".join(text + sep for text, sep in lines)


def parse_blocks(text: str, style: str) -> list[Block]:
    """Bloques del archivo. En Markdown, los marcadores dentro de ``` no cuentan."""
    pattern = _MARKER[style]
    _, lines = _split(text)
    blocks: list[Block] = []
    seen: set[str] = set()
    open_id: str | None = None
    open_line = 0
    content: list[str] = []
    in_code = False
    for number, (line, _sep) in enumerate(lines, start=1):
        if style == STYLE_HTML and _FENCE.match(line):
            in_code = not in_code
        match = None if in_code else pattern.match(line)
        if not match:
            if open_id is not None:
                content.append(line)
            continue
        kind, block_id = match.groups()
        if kind == "BEGIN":
            if open_id is not None:
                raise BlockError(f"line {number}: BEGIN of {block_id!r} nested inside {open_id!r}")
            if block_id in seen:
                raise BlockError(f"line {number}: duplicate block {block_id!r}")
            open_id, open_line, content = block_id, number, []
            continue
        if open_id is None:
            raise BlockError(f"line {number}: END of {block_id!r} without its BEGIN")
        if block_id != open_id:
            raise BlockError(f"line {number}: END {block_id!r} does not match {open_id!r}")
        blocks.append(Block(open_id, open_line, number, "\n".join(content)))
        seen.add(open_id)
        open_id = None
    if open_id is not None:
        raise BlockError(f"line {open_line}: BEGIN of {open_id!r} without its END")
    return blocks


def _find(blocks: list[Block], block_id: str) -> Block | None:
    return next((b for b in blocks if b.id == block_id), None)


def _block_lines(block_id: str, content: str, style: str) -> list[str]:
    begin, end = markers(block_id, style)
    body = content.replace("\r\n", "\n").rstrip("\n")
    inner = body.split("\n") if body else []
    for line in inner:
        if any(pattern.match(line) for pattern in _MARKER.values()):
            raise BlockError(f"the content of block {block_id!r} cannot include markers")
    return [begin, *inner, end]


def inject_text(
    text: str, block_id: str, content: str, *, style: str, position: str = "end"
) -> str:
    if position not in ("start", "end"):
        raise BlockError(f"invalid position: {position!r} (start or end)")
    new_block = _block_lines(block_id, content, style)
    existing = _find(parse_blocks(text, style), block_id)
    bom, lines = _split(text)
    newline = _newline(text)
    block = [[line, newline] for line in new_block]
    if existing is not None:
        start, end = existing.start_line - 1, existing.end_line
        block[-1][1] = lines[end - 1][1]  # conserva lo que seguía al END original
        lines[start:end] = block
        return _join(bom, lines)
    if not lines:
        return _join(bom, block)
    if position == "start":
        return _join(bom, [*block, ["", newline], *lines])
    if not lines[-1][1]:
        # El archivo no terminaba en salto de línea: se agrega uno para separar y el
        # bloque queda sin salto final, así `remove_text` sabe que tiene que quitarlo.
        lines[-1][1] = newline
        block[-1][1] = ""
    return _join(bom, [*lines, ["", newline], *block])


def replace_text(text: str, block_id: str, content: str, *, style: str) -> str:
    if _find(parse_blocks(text, style), block_id) is None:
        raise BlockError(f"block {block_id!r} does not exist")
    return inject_text(text, block_id, content, style=style)


def remove_text(text: str, block_id: str, *, style: str) -> str:
    existing = _find(parse_blocks(text, style), block_id)
    if existing is None:
        return text
    bom, lines = _split(text)
    start, end = existing.start_line - 1, existing.end_line
    # Quita también la línea en blanco que agregó inject para separar el bloque y, si
    # el bloque cerraba el archivo sin salto final, el salto que agregó a la línea previa.
    if end == len(lines) and start > 0 and lines[start - 1][0] == "":
        start -= 1
        if not lines[end - 1][1] and start > 0:
            lines[start - 1][1] = ""
    elif start == 0 and end < len(lines) and lines[end][0] == "":
        end += 1
    del lines[start:end]
    return _join(bom, lines)


# -- operaciones sobre archivos ---------------------------------------------


def _read(path: Path) -> str:
    try:
        raw = fsutil.read_bytes(path)
    except FileNotFoundError:
        return ""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BlockError(f"{path} is not valid UTF-8 ({exc.reason}); left unchanged") from exc


def _write(path: Path, old: str, new: str, *, backup: bool) -> bool:
    if new == old:
        return False
    if backup and Path(path).exists():
        fsutil.write_atomic(Path(f"{path}.{_meta.NAME}.bak"), old.encode("utf-8"))
    fsutil.write_atomic(path, new.encode("utf-8"))
    return True


def inject(
    path: Path,
    block_id: str,
    content: str,
    *,
    style: str | None = None,
    position: str = "end",
    backup: bool = False,
) -> bool:
    """Inserta o reemplaza el bloque. Devuelve si escribió."""
    style = style or style_for(path)
    old = _read(path)
    new = inject_text(old, block_id, content, style=style, position=position)
    return _write(path, old, new, backup=backup)


def replace(
    path: Path, block_id: str, content: str, *, style: str | None = None, backup: bool = False
) -> bool:
    style = style or style_for(path)
    old = _read(path)
    return _write(path, old, replace_text(old, block_id, content, style=style), backup=backup)


def remove(path: Path, block_id: str, *, style: str | None = None, backup: bool = False) -> bool:
    if not Path(path).exists():
        return False
    style = style or style_for(path)
    old = _read(path)
    return _write(path, old, remove_text(old, block_id, style=style), backup=backup)


def list_blocks(path: Path, *, style: str | None = None) -> list[Block]:
    style = style or style_for(path)
    return parse_blocks(_read(path), style)
