"""`exo init`, `sync`, `update`, `status`, `add-agent`, `remove-agent` y `uninstall`."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from exo import _meta, content, packs
from exo.adapters import KNOWN_AGENTS, detect
from exo.commands._output import emit_json, error, usage_error
from exo.core import config, tickets
from exo.installer import engine, project, stack, update, wizard


def _common(parser: argparse.ArgumentParser, *, writes: bool = True) -> None:
    parser.add_argument("--project", type=Path, default=Path("."), help="project root")
    parser.add_argument("--json", action="store_true", help="JSON output")
    if writes:
        parser.add_argument(
            "--dry-run", action="store_true", help="show what would change, without writing"
        )
        parser.add_argument(
            "--force", action="store_true", help="overwrite manual edits (takes a snapshot first)"
        )


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


_PRUNE_HELP = "also delete orphaned skills and subagents (takes a snapshot first)"


def register(sub: argparse._SubParsersAction) -> None:
    init = sub.add_parser(
        "init",
        help="adopt the engine in a project (detects the agents)",
        description=(
            "Detects the agents in use and generates only what each one needs. "
            "In an interactive terminal it asks; with --yes it uses the detection and the flags."
        ),
    )
    _common(init)
    init.add_argument(
        "--agents", type=_csv, help=f"comma-separated agents: {', '.join(KNOWN_AGENTS)}"
    )
    init.add_argument(
        "--packs", type=_csv, help="comma-separated packs (default: the suggested ones)"
    )
    init.add_argument(
        "--ticket-pattern",
        metavar="REGEX",
        help=(
            "regular expression for the project's ticket IDs (for example "
            "'[A-Z][A-Z0-9]*-\\d+' or '#\\d+'); empty for no tickets"
        ),
    )
    init.add_argument("--ticket-example", metavar="ID", help="example ticket ID shown in messages")
    init.add_argument(
        "--review-host",
        choices=config.REVIEW_HOSTS,
        help="where the repo lives (detected from the git remote if not given)",
    )
    init.add_argument(
        "--publish-command",
        metavar="CMD",
        help="command that publishes one gate as a PR comment (see the ci-and-review contract)",
    )
    init.add_argument(
        "--no-tickets",
        action="store_true",
        help="the project has no tickets (same as an empty --ticket-pattern)",
    )
    init.add_argument(
        "--mcp", action="store_true", help="enable the optional MCP server (ADR-0005)"
    )
    init.add_argument(
        "--claude-md",
        action="store_true",
        help="create CLAUDE.md with @AGENTS.md even if it does not exist",
    )
    init.add_argument("--yes", action="store_true", help="never prompt")
    init.set_defaults(handler=_init)

    sync = sub.add_parser(
        "sync",
        help="regenerate the engine files from the config and the lock",
        description=(
            "Skills and subagents that the content no longer ships (orphans) are reported "
            "and kept; --prune deletes them."
        ),
    )
    _common(sync)
    sync.add_argument("--prune", action="store_true", help=_PRUNE_HELP)
    sync.set_defaults(handler=_sync)

    update_cmd = sub.add_parser(
        "update",
        help="bring the project files to this engine version (preview by default)",
        description=(
            "Shows what this engine version changes in the project: new, modified, renamed "
            "and orphaned files, and conflicts with your edits. Writes only with --apply. "
            "Your edits are kept unless you add --force, and orphaned skills and subagents "
            "are deleted only with --prune (in a terminal, --apply asks)."
        ),
    )
    _common(update_cmd, writes=False)
    update_cmd.add_argument(
        "--apply", action="store_true", help="write the changes (takes a snapshot first)"
    )
    update_cmd.add_argument(
        "--force", action="store_true", help="overwrite your edits (takes a snapshot first)"
    )
    update_cmd.add_argument("--prune", action="store_true", help=_PRUNE_HELP)
    update_cmd.set_defaults(handler=_update)

    status = sub.add_parser("status", help="agents, packs and manual changes to generated files")
    _common(status, writes=False)
    status.set_defaults(handler=_status)

    for name, helptext in (("add-agent", "add an agent"), ("remove-agent", "remove an agent")):
        parser = sub.add_parser(name, help=helptext)
        parser.add_argument("agent")
        _common(parser)
        parser.set_defaults(handler=_add_agent if name == "add-agent" else _remove_agent)

    uninstall = sub.add_parser(
        "uninstall",
        help="remove the engine from the project and leave it as it was",
        description="Saves a safety backup outside the project first.",
    )
    _common(uninstall)
    uninstall.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    uninstall.set_defaults(handler=_uninstall)


# -- salida ---------------------------------------------------------------------

# Etiqueta en la salida de texto de las claves del JSON que no se leen tal cual.
_LABELS = {
    "safety_backup": "safety backup",
    "also_removed": "also removed (kept in the backup)",
    "kept": (
        "kept (project knowledge from discovery and your brand.json; delete them yourself if "
        "you want)"
    ),
}


def _payload(result: engine.Result, renamed: dict[str, str] | None = None) -> dict[str, Any]:
    return {
        "applied": result.applied,
        "changed": result.changed,
        "snapshot": result.snapshot,
        "actions": [vars(a) for a in result.actions],
        "conflicts": [vars(c) for c in result.conflicts],
        "orphans": [a.path for a in result.orphans],
        "renamed": dict(renamed or {}),
        "warnings": result.warnings,
    }


def _group_key(action: engine.Action) -> str:
    """Una skill se muestra como su carpeta: `.claude/skills/<nombre>/`."""
    parts = action.path.split("/")
    if action.kind == "mirror" and len(parts) >= 4:
        return "/".join(parts[:3]) + "/"
    return action.path


def _grouped(
    actions: list[engine.Action], renamed: dict[str, str], *, word: str = "renamed to"
) -> list[str]:
    """Una línea por skill (o por archivo), con la cantidad de archivos y el renombre."""
    groups: dict[str, list[engine.Action]] = {}
    for action in actions:
        groups.setdefault(_group_key(action), []).append(action)
    lines = []
    for key, items in groups.items():
        notes = []
        if key.endswith("/"):
            notes.append(f"{len(items)} file{'' if len(items) == 1 else 's'}")
        other = next((renamed[a.path] for a in items if a.path in renamed), None)
        if other is not None:
            shown = "/".join(other.split("/")[:3]) + "/" if key.endswith("/") else other
            notes.append(f"{word} {shown}")
        notes += sorted({a.detail for a in items if a.detail})
        lines.append(key + (f" ({', '.join(notes)})" if notes else ""))
    return lines


def _conflict_label(conflict: engine.Conflict, args: argparse.Namespace) -> str:
    if not conflict.forceable:
        return "unresolved"
    if not args.force:
        return "conflict"
    return "would force" if args.dry_run else "forced"


def _report(
    result: engine.Result,
    args: argparse.Namespace,
    extra: dict[str, Any],
    renamed: dict[str, str] | None = None,
) -> int:
    """Imprime el resultado. Sale con 1 si hubo conflictos sin `--force`, o si quedaron
    conflictos que `--force` no resuelve. Las huérfanas se informan, sin cambiar el código."""
    failed = bool(result.conflicts) and not args.force
    code = 1 if failed or result.unresolved else 0
    if args.json:
        emit_json({**extra, **_payload(result, renamed)})
        return code
    for key, value in extra.items():
        if key == "notes":
            for note in value:
                print(f"note: {note}")
        elif isinstance(value, list):
            print(f"{_LABELS.get(key, key)}: {', '.join(value) if value else '-'}")
        elif value is not None:
            print(f"{_LABELS.get(key, key)}: {value}")
    for warning in result.warnings:
        print(f"warning: {warning}")
    for conflict in result.conflicts:
        label = _conflict_label(conflict, args)
        print(f"{label}: {conflict.path} ({conflict.kind}): {conflict.reason}")
    if failed:
        hint = (
            "Fix the ones marked 'unresolved' by hand; --force does not overwrite them."
            if result.unresolved
            else "Review the conflicts or retry with --force (takes a snapshot first)."
        )
        print(f"nothing was written. {hint}")
        return 1
    # Una línea por archivo: varias unidades del mismo archivo (los ítems de una
    # lista, por ejemplo) se informan juntas.
    writes = list(
        dict.fromkeys((a.action, a.path) for a in result.actions if a.action in engine.WRITES)
    )
    if args.dry_run:
        print("dry-run: nothing was written")
    for action, path in writes if (args.dry_run or len(writes) <= 30) else []:
        print(f"{action}\t{path}")
    for line in _grouped(result.orphans, renamed or {}):
        print(f"orphan\t{line}")
    if not result.changed:
        print("no changes")
    else:
        counts = {name: sum(action == name for action, _ in writes) for name in engine.WRITES}
        summary = ", ".join(f"{n} {name}" for name, n in counts.items() if n)
        print(f"{'would do' if args.dry_run else 'done'}: {summary or 'lock only'}")
        if result.snapshot:
            print(f"snapshot before the changes: {result.snapshot}")
    if result.unresolved:
        done = "would be applied" if args.dry_run else "was applied"
        print(f"the rest {done}; fix the ones marked 'unresolved' by hand and retry.")
    if result.orphans:
        print(
            f"orphaned: {len(result.orphans)} files that this content no longer ships were kept "
            f"(your agents may still use them); delete them with `{_meta.NAME} sync --prune`"
        )
    return code


# -- comandos ---------------------------------------------------------------------


def _available_packs() -> list[str]:
    return list(packs.load_packs(content.content_root()))


def _init(args: argparse.Namespace) -> int:
    root = args.project.resolve()
    interactive = not args.yes and sys.stdin.isatty()
    agents = args.agents
    chosen_packs = args.packs
    if args.no_tickets and (args.ticket_pattern is not None or args.ticket_example is not None):
        return usage_error("--no-tickets cannot go with --ticket-pattern or --ticket-example")
    if args.no_tickets:
        args.ticket_pattern = ""
    if args.ticket_example is not None and args.ticket_pattern is None:
        return usage_error("--ticket-example needs --ticket-pattern")
    if args.ticket_pattern:
        try:
            tickets.compile_pattern(args.ticket_pattern)
            if args.ticket_example is not None:
                tickets.check_example(args.ticket_pattern, args.ticket_example)
        except tickets.TicketError as exc:
            return usage_error(str(exc))
    ticket_cfg = (
        wizard.ticket_config(args.ticket_pattern or None, args.ticket_example)
        if args.ticket_pattern is not None
        else None
    )
    try:
        installed = project.current_agents(root)
        if agents is None and installed is not None:
            agents = installed
        if interactive and agents is None:
            choices = wizard.choose(
                detect.detect(root), stack.detect_stack(root), _available_packs()
            )
            agents, chosen_packs, ticket_cfg = (
                choices.agents,
                chosen_packs or choices.packs,
                ticket_cfg or choices.tickets,
            )
        elif agents is None:
            detections = detect.detect(root)
            agents = detect.preselect(detections)
            _print_detections(detections)
            if not agents:
                print("warning: no agent detected; installing the generic base (AGENTS.md)")
        if chosen_packs is None and installed is None:
            report = stack.detect_stack(root)
            available = _available_packs()
            chosen_packs = [p for p in report.suggested if p in available]
            offered = [p for p in report.offered if p in available]
            if offered:
                packs_flag = ",".join([*chosen_packs, *offered])
                print(
                    f"note: {', '.join(offered)} is available for this existing codebase (reverse "
                    f"engineering); install it with --packs {packs_flag}"
                )
        kwargs = dict(
            agents=agents,
            packs=chosen_packs,
            mcp=True if args.mcp else None,
            tickets=ticket_cfg,
            review=_review(args),
            detect_host=True,
            claude_md=args.claude_md,
            force=args.force,
        )
        if interactive and not args.dry_run:
            preview = project.sync(root, dry_run=True, **kwargs)
            summary = [
                f"{a.action} {a.path}" for a in preview.engine.actions if a.action in engine.WRITES
            ]
            if not wizard.confirm(summary or ["no changes"]):
                print("cancelled")
                return 1
        result = project.sync(root, dry_run=args.dry_run, **kwargs)
    except (project.ProjectError, ValueError, OSError) as exc:
        return error(str(exc))
    return _report(
        result.engine,
        args,
        {"agents": result.agents, "packs": result.packs, "notes": result.notes},
        result.renamed,
    )


def _print_detections(detections: list[detect.Detection]) -> None:
    """ADR-0006: sin preguntar, se instala lo detectado con certeza y se informa el resto."""
    for item in detections:
        evidence = ", ".join(item.evidence)
        if item.strong:
            print(f"detected: {item.agent} ({evidence})")
        else:
            print(
                f"unconfirmed: {item.agent} ({evidence}); if you use it, run "
                f"`{_meta.NAME} add-agent {item.agent}`"
            )


def _not_installed(root: Path) -> int:
    return error(f"the engine is not installed in {root}; run `{_meta.NAME} init`")


def _sync(args: argparse.Namespace) -> int:
    root = args.project.resolve()
    try:
        if project.current_agents(root) is None:
            return _not_installed(root)
        result = project.sync(root, force=args.force, dry_run=args.dry_run, prune=args.prune)
    except (project.ProjectError, ValueError, OSError) as exc:
        return error(str(exc))
    return _report(
        result.engine,
        args,
        {"agents": result.agents, "packs": result.packs, "notes": result.notes},
        result.renamed,
    )


def _update(args: argparse.Namespace) -> int:
    """Vista previa por defecto. Con `--apply` en una terminal y huérfanas sin `--prune`,
    pregunta si borrarlas; sin terminal, nunca."""
    root = args.project.resolve()
    try:
        if project.current_agents(root) is None:
            return _not_installed(root)
        prune = args.prune
        if args.apply and not prune and not args.json and sys.stdin.isatty():
            preview = update.update(root, force=args.force)
            if preview.engine.orphans:
                print("orphaned (no longer shipped by this version):")
                for line in _grouped(preview.engine.orphans, preview.sync.renamed):
                    print(f"  {line}")
                prune = wizard.yes("Delete them too? The rest of the update is applied anyway.")
        result = update.update(root, apply=args.apply, force=args.force, prune=prune)
    except (project.ProjectError, ValueError, OSError) as exc:
        return error(str(exc))
    return _update_report(result, args)


def _section(title: str, actions: list[engine.Action], renamed: dict[str, str], word: str) -> None:
    lines = _grouped(actions, renamed, word=word)
    if lines:
        print(f"{title}:")
        for line in lines:
            print(f"  {line}")


def _update_report(result: update.UpdateResult, args: argparse.Namespace) -> int:
    """Sale con 1 si quedaron conflictos: lo editado que se conservó sin `--force`, o lo que
    ni `--force` resuelve. Lo demás se aplicó igual."""
    found = result.engine
    renamed = result.sync.renamed
    kept = [c for c in found.conflicts if c.forceable and not args.force]
    code = 1 if kept or found.unresolved else 0
    migration = result.sync.config_migration
    if args.json:
        emit_json(
            {
                "from_version": result.from_version,
                "to_version": result.to_version,
                "up_to_date": result.up_to_date,
                "new": result.paths("create"),
                "modified": result.paths("update"),
                "removed": result.paths("remove"),
                "config_migration": (
                    {"from": migration[0], "to": migration[1], "saved": result.sync.config_written}
                    if migration
                    else None
                ),
                "notes": result.sync.notes,
                **_payload(found, renamed),
            }
        )
        return code
    for note in result.sync.notes:
        print(f"note: {note}")
    for warning in found.warnings:
        print(f"warning: {warning}")
    if result.from_version == result.to_version:
        print(f"engine: {result.to_version} (the lock is already at this version)")
    else:
        print(f"engine: {result.from_version or 'unknown version'} -> {result.to_version}")
    if migration:
        state = "saved" if result.sync.config_written else "saved with --apply"
        if found.applied and not result.sync.config_written:
            state = "not saved"
        print(f"config: schema {migration[0]} -> {migration[1]} ({state})")

    def of(action: str) -> list[engine.Action]:
        return [
            a for a in found.actions if a.action == action and a.detail != update.OUTSIDE_THE_LOCK
        ]

    back = {new: old for old, new in renamed.items()}
    _section("new", of("create"), back, "renamed from")
    _section("modified", of("update"), {}, "")
    _section("removed", of("remove"), renamed, "renamed to")
    title = "orphaned (no longer shipped; kept until you prune them)"
    _section(title, found.orphans, renamed, "renamed to")
    for conflict in found.conflicts:
        if not conflict.forceable:
            label = "unresolved"
        elif args.force:
            label = "forced" if args.apply else "would force"
        else:
            label = "kept"
        print(f"{label}: {conflict.path} ({conflict.kind}): {conflict.reason}")
    if not args.apply:
        if result.up_to_date:
            print(f"up to date: nothing to change for {_meta.NAME} {result.to_version}")
        else:
            print(f"preview: nothing was written; apply it with `{_meta.NAME} update --apply`")
    elif not found.changed:
        print("no changes")
    else:
        writes = list(
            dict.fromkeys((a.action, a.path) for a in found.actions if a.action in engine.WRITES)
        )
        counts = {name: sum(action == name for action, _ in writes) for name in engine.WRITES}
        summary = ", ".join(f"{n} {name}" for name, n in counts.items() if n)
        print(f"done: {summary or 'lock only'}")
        if found.snapshot:
            print(f"snapshot before the changes: {found.snapshot}")
    if kept:
        files = f"{len(kept)} file{'' if len(kept) == 1 else 's'}"
        print(
            f"kept your edits in {files}; overwrite them with "
            f"`{_meta.NAME} update --apply --force` (takes a snapshot first)"
        )
    if found.unresolved:
        print("fix the ones marked 'unresolved' by hand and retry.")
    if found.orphans:
        print(
            f"orphaned: {len(found.orphans)} files kept (your agents may still use them); "
            f"delete them with `{_meta.NAME} update --apply --prune`"
        )
    return code


def _change_agents(args: argparse.Namespace, add: bool) -> int:
    root = args.project.resolve()
    try:
        installed = project.current_agents(root)
        if installed is None:
            return _not_installed(root)
        current = [a for a in installed if a != "generic"]
        if add:
            agents = [*current, args.agent] if args.agent not in current else current
        elif args.agent not in current:
            return error(
                f"{args.agent} is not one of the project agents ({', '.join(current) or '-'})"
            )
        else:
            agents = [a for a in current if a != args.agent]
        result = project.sync(root, agents=agents, force=args.force, dry_run=args.dry_run)
    except (project.ProjectError, ValueError, OSError) as exc:
        return error(str(exc))
    return _report(
        result.engine, args, {"agents": result.agents, "notes": result.notes}, result.renamed
    )


def _add_agent(args: argparse.Namespace) -> int:
    return _change_agents(args, add=True)


def _remove_agent(args: argparse.Namespace) -> int:
    return _change_agents(args, add=False)


def _status(args: argparse.Namespace) -> int:
    try:
        info = project.status(args.project)
    except (ValueError, OSError) as exc:
        return error(str(exc))
    drift = [{"path": d.entry.path, "kind": d.entry.kind, "status": d.status} for d in info.drift]
    if args.json:
        emit_json(
            {
                "installed": info.installed,
                "agents": info.agents,
                "packs": info.packs,
                "engine_version": _meta.VERSION,
                "lock_version": info.lock_version,
                "files": info.files,
                "drift": drift,
                "warnings": info.warnings,
            }
        )
        return 0
    if not info.installed:
        print(f"the engine is not installed; run `{_meta.NAME} init`")
        return 0
    # Diferido: `sync` y los demás comandos del módulo no cargan la observabilidad.
    from exo import status_view

    style = status_view.Style(color=status_view.use_color(sys.stdout, os.environ))
    for line in status_view.render(status_view.gather(args.project, info), style):
        print(line)
    return 0


def _uninstall(args: argparse.Namespace) -> int:
    if not args.yes and not args.dry_run:
        if not sys.stdin.isatty():
            return usage_error(
                "uninstall deletes generated files; in non-interactive mode add --yes"
            )
        if not wizard.confirm(  # pragma: no cover
            [f"remove the engine from {args.project.resolve()}"]
        ):
            print("cancelled")
            return 1
    root = args.project.resolve()
    if not (root / _meta.PROJECT_DIR).exists():
        if args.json:
            emit_json({"installed": False, "applied": False, "changed": False})
        else:
            print(f"the engine is not installed in {root}; nothing to do")
        return 0
    try:
        result = project.uninstall(root, force=args.force, dry_run=args.dry_run)
    except (project.ProjectError, ValueError, OSError) as exc:
        return error(str(exc))
    backup = str(result.backup) if result.backup else None
    extra: dict[str, Any] = {"safety_backup": backup}
    if result.also_removed:
        extra["also_removed"] = result.also_removed
    if result.kept:
        extra["kept"] = result.kept
    return _report(result.engine, args, extra)


def _review(args: argparse.Namespace) -> dict[str, Any] | None:
    pairs = (("host", args.review_host), ("publish_command", args.publish_command))
    found = {key: value for key, value in pairs if value}
    return found or None
