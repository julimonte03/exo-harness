"""Frontmatter con un subconjunto de YAML, sin PyYAML.

Alcanza para el estándar Agent Skills y los subagentes:
- escalares (texto, `true`/`false`, `null`/`~`, enteros), con comillas simples o dobles;
- listas en bloque (`- x`) y en línea (`[a, b]`);
- un nivel de mapa anidado (`metadata:`);
- bloques `|`, `|-`, `>` y `>-` en el primer nivel;
- comentarios de línea completa y al final de un escalar sin comillas.

En modo estricto (`strict=True`, el que usa `exo validate`) todo lo que quede
fuera del subconjunto es un `FrontmatterError` con número de línea. En modo
tolerante se ignora lo que no se entiende.
"""

from __future__ import annotations

import re
from typing import Any

_DELIMITER = "---"
_KEY = re.compile(r"^([A-Za-z0-9_][A-Za-z0-9_.-]*):(?: +(.*))?$")
_INT = re.compile(r"^[-+]?\d+$")
_BLOCK_INDICATORS = ("|", "|-", ">", ">-")
_ESCAPES = {"\\": "\\", '"': '"', "n": "\n", "t": "\t", "/": "/"}
_UNSUPPORTED_START = {
    "&": "no soportado: anclas",
    "*": "no soportado: alias",
    "!": "no soportado: tags",
    "{": "no soportado: mapas en línea",
}


class FrontmatterError(ValueError):
    def __init__(self, message: str, line: int) -> None:
        super().__init__(f"línea {line}: {message}")
        self.message = message
        self.line = line


class _Skip(Exception):
    """Error tolerado en modo no estricto: se descarta la clave actual."""


def parse(text: str, *, strict: bool = False) -> tuple[dict[str, Any], str]:
    """Devuelve `(datos, cuerpo)`. Sin frontmatter, en modo tolerante: `({}, text)`."""
    source = text[1:] if text.startswith("﻿") else text
    lines = source.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != _DELIMITER:
        if strict:
            raise FrontmatterError(
                "falta el frontmatter: el archivo tiene que empezar con '---'", 1
            )
        return {}, text
    close = next(
        (i for i in range(1, len(lines)) if lines[i].rstrip("\r\n") == _DELIMITER), None
    )
    if close is None:
        if strict:
            raise FrontmatterError("el frontmatter no se cierra con una línea '---'", 1)
        return {}, text
    block = [(i + 1, lines[i].rstrip("\r\n")) for i in range(1, close)]
    data = _Parser(block, strict).document()
    return data, "".join(lines[close + 1 :])


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _is_blank_or_comment(line: str) -> bool:
    stripped = line.strip()
    return not stripped or stripped.startswith("#")


class _Parser:
    def __init__(self, lines: list[tuple[int, str]], strict: bool) -> None:
        self.lines = lines
        self.strict = strict
        self.i = 0

    def fail(self, message: str, line: int) -> None:
        if self.strict:
            raise FrontmatterError(message, line)
        raise _Skip

    def check_tabs(self, lineno: int, line: str) -> None:
        if "\t" in line:
            self.fail("tabulación no permitida; usá espacios", lineno)

    # -- documento --------------------------------------------------------

    def document(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        while self.i < len(self.lines):
            lineno, line = self.lines[self.i]
            self.i += 1
            if _is_blank_or_comment(line):
                continue
            try:
                self.check_tabs(lineno, line)
                if _indent(line):
                    self.fail("indentación inesperada", lineno)
                match = _KEY.match(line)
                if not match:
                    self.fail("se esperaba 'clave: valor'", lineno)
                    continue  # pragma: no cover - fail siempre lanza
                key = match.group(1)
                value = self.value((match.group(2) or "").rstrip(), lineno, parent_indent=0)
                if key in data and self.strict:
                    self.fail(f"clave repetida: {key!r}", lineno)
                data[key] = value
            except _Skip:
                continue
        return data

    # -- valores ----------------------------------------------------------

    def value(self, raw: str, lineno: int, *, parent_indent: int, nested: bool = False) -> Any:
        if raw.startswith("#"):
            raw = ""
        if raw in _BLOCK_INDICATORS:
            if nested:
                self.fail(
                    "solo se admite un nivel de anidamiento: bloques | y > van en el primer nivel",
                    lineno,
                )
            return self.block_scalar(raw, parent_indent)
        if raw[:1] in ("|", ">"):
            self.fail(f"indicador de bloque no soportado: {raw!r}", lineno)
        if raw == "":
            return self.children(lineno, parent_indent, nested)
        return self.inline(raw, lineno)

    def inline(self, raw: str, lineno: int) -> Any:
        if raw[0] in _UNSUPPORTED_START:
            self.fail(_UNSUPPORTED_START[raw[0]], lineno)
        if raw.startswith("["):
            return self.flow_list(raw, lineno)
        if raw[0] in "\"'":
            text, rest = self.quoted(raw, lineno)
            if rest.strip() and not rest.strip().startswith("#"):
                self.fail("texto inesperado después de la comilla de cierre", lineno)
            return text
        return _plain(raw)

    def quoted(self, raw: str, lineno: int) -> tuple[str, str]:
        quote = raw[0]
        out: list[str] = []
        i = 1
        while i < len(raw):
            char = raw[i]
            if quote == "'" and char == "'":
                if raw[i + 1 : i + 2] == "'":
                    out.append("'")
                    i += 2
                    continue
                return "".join(out), raw[i + 1 :]
            if quote == '"' and char == "\\":
                escaped = raw[i + 1 : i + 2]
                if escaped not in _ESCAPES:
                    self.fail(f"escape no soportado: '\\{escaped}'", lineno)
                out.append(_ESCAPES[escaped])
                i += 2
                continue
            if quote == '"' and char == '"':
                return "".join(out), raw[i + 1 :]
            out.append(char)
            i += 1
        self.fail("comilla sin cerrar", lineno)
        return "", ""  # pragma: no cover - fail siempre lanza

    def flow_list(self, raw: str, lineno: int) -> list[Any]:
        items: list[Any] = []
        i = 1
        while True:
            while i < len(raw) and raw[i] == " ":
                i += 1
            if i >= len(raw):
                self.fail("corchete sin cerrar en la lista", lineno)
            char = raw[i]
            if char == "]" and not items:
                rest = raw[i + 1 :]
                break
            if char in "[{":
                self.fail("no soportado: listas o mapas anidados en una lista en línea", lineno)
            if char in "\"'":
                text, remainder = self.quoted(raw[i:], lineno)
                items.append(text)
                i = len(raw) - len(remainder)
                while i < len(raw) and raw[i] == " ":
                    i += 1
            else:
                end = i
                while end < len(raw) and raw[end] not in ",]":
                    end += 1
                items.append(_plain(raw[i:end].strip()))
                i = end
            if i >= len(raw):
                self.fail("corchete sin cerrar en la lista", lineno)
            if raw[i] == ",":
                i += 1
                continue
            if raw[i] == "]":
                rest = raw[i + 1 :]
                break
            self.fail("se esperaba ',' o ']' en la lista", lineno)
        if rest.strip() and not rest.strip().startswith("#"):
            self.fail("texto inesperado después de ']'", lineno)
        return items

    def block_scalar(self, indicator: str, parent_indent: int) -> str:
        content: list[str] = []
        block_indent: int | None = None
        while self.i < len(self.lines):
            _, line = self.lines[self.i]
            if not line.strip():
                content.append("")
                self.i += 1
                continue
            indent = _indent(line)
            if indent <= parent_indent or (block_indent is not None and indent < block_indent):
                break
            if block_indent is None:
                block_indent = indent
            content.append(line[block_indent:])
            self.i += 1
        while content and content[-1] == "":
            content.pop()
        if not content:
            return ""
        if indicator.startswith("|"):
            text = "\n".join(content)
        else:
            paragraphs: list[tuple[str, int]] = []
            blanks = 0
            current: list[str] = []
            for line in content:
                if line == "":
                    if current:
                        paragraphs.append((" ".join(current), blanks))
                        current, blanks = [], 0
                    blanks += 1
                else:
                    current.append(line)
            paragraphs.append((" ".join(current), blanks))
            text = paragraphs[0][0]
            for paragraph, gap in paragraphs[1:]:
                text += "\n" * gap + paragraph
        return text if indicator.endswith("-") else text + "\n"

    def children(self, lineno: int, parent_indent: int, nested: bool) -> Any:
        first = self.peek_content()
        if first is None:
            return None
        child_lineno, child = first
        indent = _indent(child)
        is_item = child.lstrip(" ").startswith("-")
        if indent <= parent_indent and not (is_item and not nested and indent == parent_indent):
            return None
        if nested:
            self.fail("solo se admite un nivel de anidamiento", child_lineno)
        if is_item:
            return self.sequence(indent)
        return self.mapping(indent)

    def peek_content(self) -> tuple[int, str] | None:
        j = self.i
        while j < len(self.lines):
            lineno, line = self.lines[j]
            if not _is_blank_or_comment(line):
                return lineno, line
            j += 1
        return None

    def sequence(self, indent: int) -> list[Any]:
        items: list[Any] = []
        while self.i < len(self.lines):
            lineno, line = self.lines[self.i]
            if _is_blank_or_comment(line):
                self.i += 1
                continue
            current = _indent(line)
            stripped = line.lstrip(" ")
            if current < indent or (current == indent == 0 and not stripped.startswith("-")):
                break
            self.check_tabs(lineno, line)
            if current > indent:
                self.fail("solo se admite un nivel de anidamiento", lineno)
            if not (stripped == "-" or stripped.startswith("- ")):
                self.fail("mezcla de lista y mapa en el mismo nivel", lineno)
            self.i += 1
            raw = stripped[1:].strip()
            if raw.startswith("["):
                self.fail("no soportado: listas anidadas", lineno)
            items.append(self.inline(raw, lineno) if raw and not raw.startswith("#") else None)
        return items

    def mapping(self, indent: int) -> dict[str, Any]:
        result: dict[str, Any] = {}
        while self.i < len(self.lines):
            lineno, line = self.lines[self.i]
            if _is_blank_or_comment(line):
                self.i += 1
                continue
            current = _indent(line)
            if current == 0:
                break
            self.check_tabs(lineno, line)
            if current > indent:
                self.fail("solo se admite un nivel de anidamiento", lineno)
            if current < indent:
                self.fail("indentación inconsistente en el mapa", lineno)
            stripped = line[indent:]
            if stripped.startswith("-"):
                self.fail("mezcla de lista y mapa en el mismo nivel", lineno)
            match = _KEY.match(stripped)
            if not match:
                self.fail("se esperaba 'clave: valor'", lineno)
                continue  # pragma: no cover - fail siempre lanza
            self.i += 1
            key = match.group(1)
            if key in result and self.strict:
                self.fail(f"clave repetida: {key!r}", lineno)
            raw = (match.group(2) or "").rstrip()
            result[key] = self.value(raw, lineno, parent_indent=indent, nested=True)
        return result


def _plain(raw: str) -> Any:
    comment = raw.find(" #")
    text = (raw[:comment] if comment >= 0 else raw).strip()
    lowered = text.lower()
    if lowered in ("true", "false"):
        return lowered == "true"
    if lowered in ("null", "~"):
        return None
    if _INT.match(text):
        return int(text)
    return text
