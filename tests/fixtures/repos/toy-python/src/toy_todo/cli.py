"""Command line: `python -m toy_todo add|list|done`."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from toy_todo.store import TaskStore

DEFAULT_FILE = "tasks.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="toy_todo", description="A tiny to-do list.")
    parser.add_argument(
        "--file", type=Path, default=Path(os.environ.get("TOY_TODO_FILE", DEFAULT_FILE))
    )
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add", help="add a task")
    add.add_argument("title")
    listing = sub.add_parser("list", help="list the tasks")
    listing.add_argument("--pending", action="store_true", help="only the pending ones")
    done = sub.add_parser("done", help="mark a task as done")
    done.add_argument("id", type=int)
    args = parser.parse_args(argv)

    store = TaskStore(args.file)
    if args.command == "add":
        task = store.add(args.title)
        print(f"added {task.id}: {task.title}")
    elif args.command == "list":
        for task in store.list(include_done=not args.pending):
            mark = "x" if task.done else " "
            print(f"[{mark}] {task.id}: {task.title}")
    else:
        try:
            task = store.complete(args.id)
        except KeyError as exc:
            print(f"error: {exc.args[0]}")
            return 1
        print(f"done {task.id}: {task.title}")
    return 0
