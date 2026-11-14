"""Task storage in a JSON file."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Task:
    id: int
    title: str
    done: bool = False


class TaskStore:
    """Keeps the task list in a JSON file; every change is saved immediately."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def _load(self) -> list[Task]:
        if not self.path.exists():
            return []
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return [Task(**item) for item in raw]

    def _save(self, tasks: list[Task]) -> None:
        self.path.write_text(
            json.dumps([asdict(t) for t in tasks], indent=2) + "\n", encoding="utf-8"
        )

    def add(self, title: str) -> Task:
        tasks = self._load()
        task = Task(id=max((t.id for t in tasks), default=0) + 1, title=title)
        tasks.append(task)
        self._save(tasks)
        return task

    def complete(self, task_id: int) -> Task:
        tasks = self._load()
        for task in tasks:
            if task.id == task_id:
                task.done = True
                self._save(tasks)
                return task
        raise KeyError(f"no task with id {task_id}")

    def list(self, *, include_done: bool = True) -> list[Task]:
        return [t for t in self._load() if include_done or not t.done]
