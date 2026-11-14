from pathlib import Path

import pytest
from toy_todo.store import TaskStore


def test_add_and_list(tmp_path: Path) -> None:
    store = TaskStore(tmp_path / "tasks.json")
    first = store.add("buy milk")
    second = store.add("call mom")
    assert (first.id, second.id) == (1, 2)
    assert [t.title for t in store.list()] == ["buy milk", "call mom"]


def test_complete_and_pending(tmp_path: Path) -> None:
    store = TaskStore(tmp_path / "tasks.json")
    store.add("buy milk")
    store.add("call mom")
    store.complete(1)
    assert [t.title for t in store.list(include_done=False)] == ["call mom"]
    assert store.list()[0].done is True


def test_complete_unknown_task(tmp_path: Path) -> None:
    with pytest.raises(KeyError):
        TaskStore(tmp_path / "tasks.json").complete(9)
