"""`exo validate`: valida el contenido canónico (packs, skills, subagentes, reglas) y, con
`--docs`, los conteos y los subcomandos que citan los docs (F8, D-48)."""

from __future__ import annotations

import argparse
from pathlib import Path

from exo import _meta, commands, content
from exo.commands._output import emit_json, error
from exo.validate import DocsReport, doc_counts, doc_files, validate, validate_docs


def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "validate",
        help="validate the engine content (or the content at --root)",
        description="Exits with 1 if there are errors. Warnings do not change the exit code.",
    )
    parser.add_argument("--root", type=Path, help="root of a content tree (with packs/ and rules/)")
    parser.add_argument(
        "--docs",
        type=Path,
        action="append",
        metavar="PATH",
        help=(
            "also check the Markdown docs at PATH (a file, or the .md files of a folder, not "
            f"its subfolders): count markers must match the content and every `{_meta.NAME} "
            "<command>` cited in code must exist; repeatable"
        ),
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.set_defaults(handler=run)


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def _doc_files(paths: list[Path]) -> list[Path] | str:
    """Los archivos a revisar, o el mensaje de error si una ruta no sirve."""
    files: list[Path] = []
    for path in paths:
        if not path.exists():
            return f"docs path {path} does not exist; pass a Markdown file or a folder"
        found = doc_files(path)
        if not found:
            return f"no Markdown files in {path} (subfolders are not searched)"
        files += found
    return files


def run(args: argparse.Namespace) -> int:
    try:
        root = args.root if args.root is not None else content.content_root()
    except content.ContentError as exc:
        return error(str(exc))
    files: list[Path] = []
    if args.docs:
        found = _doc_files(args.docs)
        if isinstance(found, str):
            return error(found)
        files = found
    report = validate(root)
    docs: DocsReport | None = None
    if args.docs:
        known = {name for names in commands.MODULES.values() for name in names}
        docs = validate_docs(files, doc_counts(report), known)
    ok = report.ok and (docs is None or docs.ok)
    if args.json:
        payload = {
            "ok": ok,
            "root": str(root),
            "counts": report.counts,
            "errors": [vars(f) for f in report.errors],
            "warnings": [vars(f) for f in report.warnings],
        }
        if docs is not None:
            payload["docs"] = {
                "files": [p.as_posix() for p in docs.files],
                "markers": docs.markers,
                "commands": docs.commands,
                "errors": [vars(f) for f in docs.errors],
            }
        emit_json(payload)
        return 0 if ok else 1
    for finding in report.errors + (docs.errors if docs else []):
        print(f"{finding.path}:{finding.line}: error: {finding.message}")
    for finding in report.warnings:
        print(f"{finding.path}:{finding.line}: warning: {finding.message}")
    counts = report.counts
    summary = (
        f"content: {counts['packs']} packs, {counts['skills']} skills, "
        f"{counts['subagents']} subagents, {counts['shared']} shared contracts"
    )
    print(f"{summary}: all valid" if report.ok else f"{summary}: {len(report.errors)} errors")
    if docs is not None:
        checked = (
            f"docs: {_plural(len(docs.files), 'file')}, {_plural(docs.markers, 'count marker')}, "
            f"{_plural(docs.commands, 'command')}"
        )
        print(f"{checked}: all valid" if docs.ok else f"{checked}: {len(docs.errors)} errors")
    return 0 if ok else 1
