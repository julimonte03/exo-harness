"""`exo registry`: genera el registro de skills del proyecto."""

from __future__ import annotations

import argparse
from pathlib import Path

from exo import content, packs, registry
from exo.commands._output import emit_json, error
from exo.core import fsutil


def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser(
        "registry",
        help="genera el registro de skills (skill-registry.md)",
        description=(
            "Lista las skills con su pack, descripción y ruta. Por defecto usa todo el "
            "contenido del motor; con --from, las skills de un directorio."
        ),
    )
    parser.add_argument("--project", type=Path, default=Path("."), help="raíz del proyecto")
    parser.add_argument("--from", dest="source", type=Path, help="directorio con skills")
    parser.add_argument("--stdout", action="store_true", help="imprime en lugar de escribir")
    parser.add_argument("--json", action="store_true", help="salida JSON")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    try:
        if args.source is not None:
            if not args.source.is_dir():
                return error(f"no existe el directorio {args.source}")
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
        print(f"{target}: " + ("actualizado" if changed else "sin cambios"))
    return 0
