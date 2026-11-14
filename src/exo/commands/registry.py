"""`exo registry`: genera el registro de skills del proyecto."""

from __future__ import annotations

import argparse
from pathlib import Path

from exo import content, packs, registry
from exo.commands._output import emit_json, error
from exo.core import fsutil, lock


def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "registry",
        help="generate the skill registry (skill-registry.md)",
        description=(
            "Lists the skills with their pack, description and path. By default it uses all "
            "the engine content; with --from, the skills in a directory."
        ),
    )
    parser.add_argument("--project", type=Path, default=Path("."), help="project root")
    parser.add_argument("--from", dest="source", type=Path, help="directory with skills")
    parser.add_argument("--stdout", action="store_true", help="print instead of writing")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    try:
        if args.source is not None:
            if not args.source.is_dir():
                return error(f"directory {args.source} does not exist")
            skills = packs.discover_skills(args.source)
            base = args.project
        else:
            base = content.content_root()
            skills = packs.load_collection(base).skills
    except (content.ContentError, ValueError, OSError) as exc:
        return error(str(exc))
    text = registry.render(skills, base=base)
    if args.stdout:
        print(text, end="")
        return 0
    target = registry.registry_path(args.project)
    if _installed(args.project, target):
        return error(
            f"{target} belongs to the engine installation (it is in the lock); writing it here "
            "would make the next sync report a conflict. Run `exo sync` to regenerate it, or "
            "use --stdout to print a registry without writing it"
        )
    changed = fsutil.write_if_changed(target, text.encode("utf-8"))
    if args.json:
        emit_json(
            {
                "path": str(target),
                "changed": changed,
                "skills": [
                    {"name": s.name, "pack": s.pack, "description": s.description}
                    for s in sorted(skills, key=lambda s: s.name)
                ],
            }
        )
    else:
        print(f"{target}: " + ("updated" if changed else "unchanged"))
    return 0


def _installed(project: Path, target: Path) -> bool:
    """¿El registro es un archivo del motor que el lock del proyecto controla?"""
    try:
        data = lock.read(project)
    except lock.LockError:
        return True  # ante la duda, no se pisa nada
    if data is None:
        return False
    rel = target.relative_to(project).as_posix()
    return any(entry.path == rel for entry in data.files)
