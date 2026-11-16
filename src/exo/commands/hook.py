"""`exo hook <nombre>`: lo que corren los git hooks del motor (D-21, ADR-0014).

Lo llaman los scripts de `<carpeta del motor>/githooks/` (o los bloques en husky).
Sale con 1 si el hook tiene que frenar el commit o el push.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from exo import _meta
from exo.governance import hookrun


def register(sub: argparse._SubParsersAction) -> None:
    group = sub.add_parser(
        "hook",
        help="run one of the engine's git hooks (git calls this)",
        description=(
            f"The git hooks that `{_meta.NAME} init` installs call these. Skipping them with "
            f"--no-verify is possible; CI still runs `{_meta.NAME} check`, which is the real gate."
        ),
    )
    group.set_defaults(handler=lambda _a: (group.print_help(), 0)[1])
    actions = group.add_subparsers(dest="hook_command", metavar="<hook>")
    message = actions.add_parser("commit-msg", help="check the commit message")
    message.add_argument("message_file", type=Path)
    _common(message)
    message.set_defaults(handler=_commit_msg)
    staged = actions.add_parser("pre-commit", help="check what is staged")
    _common(staged)
    staged.set_defaults(handler=_pre_commit)
    push = actions.add_parser("pre-push", help="check what is pushed (refs on stdin)")
    push.add_argument("remote", nargs="?", default="")
    push.add_argument("url", nargs="?", default="")
    _common(push)
    push.set_defaults(handler=_pre_push)


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", type=Path, default=Path("."), help="project root")


def _report(name: str, result: hookrun.HookResult) -> int:
    for warning in result.warnings:
        print(f"{_meta.NAME} {name}: warning: {warning}", file=sys.stderr)
    if result.ok:
        return 0
    print(f"{_meta.NAME} {name}: blocked", file=sys.stderr)
    for problem in result.errors:
        print(f"  - {problem}", file=sys.stderr)
    print(
        f"Fix it and try again. `--no-verify` skips the hook, but CI still runs "
        f"`{_meta.NAME} check`.",
        file=sys.stderr,
    )
    return 1


def _commit_msg(args: argparse.Namespace) -> int:
    return _report("commit-msg", hookrun.commit_msg(args.project, args.message_file))


def _pre_commit(args: argparse.Namespace) -> int:
    return _report("pre-commit", hookrun.pre_commit(args.project))


def _pre_push(args: argparse.Namespace) -> int:
    # Git pasa las refs por stdin; el framework pre-commit, en variables de entorno.
    interactive = sys.stdin is None or sys.stdin.isatty()
    lines = [] if interactive else sys.stdin.read().splitlines()
    if not any(line.strip() for line in lines):
        lines = hookrun.push_lines_from_env()
    return _report("pre-push", hookrun.pre_push(args.project, args.remote, lines))
