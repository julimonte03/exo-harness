from pathlib import Path

import pytest
from toy_todo.cli import main


def test_add_list_done(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    file = str(tmp_path / "tasks.json")
    assert main(["--file", file, "add", "buy milk"]) == 0
    assert main(["--file", file, "done", "1"]) == 0
    assert main(["--file", file, "list"]) == 0
    assert "[x] 1: buy milk" in capsys.readouterr().out


def test_done_unknown(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--file", str(tmp_path / "tasks.json"), "done", "3"]) == 1
    assert "no task with id 3" in capsys.readouterr().out
