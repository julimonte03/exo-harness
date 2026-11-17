# Tests with pytest

Conventions for `python-patterns`. The project's existing tests win on layout, naming and fixtures.

## Layout and names

- Tests live where the project keeps them: usually `tests/` mirroring the package (`src/invoices/billing/tax.py` is tested in `tests/test_billing.py` or `tests/billing/test_tax.py`).
- File `test_<unit>.py`; function `test_<behavior>`: `test_overdue_invoice_adds_late_fee`, not `test_tax_2`.
- When the change has a test-spec.md, name each test as its test case says, so verify can follow scenario to test.

## Shape of a test

```python
def test_complete_unknown_task_raises_key_error(tmp_path: Path) -> None:
    store = TaskStore(tmp_path / "tasks.json")

    with pytest.raises(KeyError, match="no task with id 9"):
        store.complete(9)
```

- Arrange, act, assert, separated by blank lines.
- One behavior per test; several asserts are fine when they describe that one behavior.
- Assert on outcomes the user sees (return values, files written, exit codes, HTTP responses), not on private attributes.

## Tools of the trade

| Need | Use |
|---|---|
| Files and folders | `tmp_path` |
| Environment variables, attributes, the current directory | `monkeypatch.setenv`, `monkeypatch.setattr`, `monkeypatch.chdir` |
| Many cases of one rule | `@pytest.mark.parametrize("amount, expected", [...], ids=[...])` |
| Errors | `pytest.raises(ErrorType, match="...")` |
| Warnings | `pytest.warns` |
| Output of a CLI | `capsys.readouterr()`, and the return code of `main(argv)` |
| Shared setup | a fixture in the nearest `conftest.py`; scope `function` unless setup is slow and the object is immutable |
| Logs | `caplog`, asserting on the message and the level |
| An HTTP API | the framework's test client (FastAPI and Starlette `TestClient`, Django `Client`, Flask `test_client`) |

## What not to do

- **No network:** fake the client behind its interface, or use the HTTP library's mock transport (`httpx.MockTransport`, `responses`) when the project already has it.
- **No real time:** inject the clock; no `time.sleep` to wait for something.
- **No order between tests,** no shared mutable module state; each test builds what it needs.
- **No test that passes without the behavior:** check that it fails when you break the code (or, with strict TDD, that it failed first).
- **No giant fixtures:** small factory functions (`make_invoice(total="100.00")`) beat a fixture that builds the world.
- **No mocking of what you own** when the real object is cheap: use the real dataclass, a temporary file, an in-memory SQLite database if the project's tests already do.

## Running

- Use the exact command from `.exo/context.md` (`python -m pytest`, `uv run pytest`, `pytest -q`), with the project's markers and options.
- Run the narrowest set first (`python -m pytest tests/test_export.py`), then the whole suite before you report.
- Report passed and failed counts. A failure that existed before your change needs evidence (the same failure on the base branch or in CI); otherwise it is yours.
- When you cannot run pytest, give the exact command and say the tests were not run.
