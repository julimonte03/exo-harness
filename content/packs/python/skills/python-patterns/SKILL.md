---
name: python-patterns
description: >-
  Stack router of the python pack: the Python conventions to follow when you
  design, write or change Python code. Pythonic idioms, PEP 8 with the
  project's formatter and linter, type hints, package structure, exception
  hierarchies, logging, resource handling and pytest tests, always after
  .exo/context.md and the code that is already there. It also says which skill
  to load next: python-reviewer to review a diff, the dependency scanner when
  a dependency changes, and the security and test skills. The SDD design and
  apply phases load it as the stack router of a Python project. Use it when
  you add a module, a function, a CLI command, an endpoint or a test to a
  Python codebase, or when someone asks how to structure or type Python code.
  Triggers: "write this in Python", "add a Python module", "pythonic way",
  "PEP 8", "type hints", "structure this Python package", "add a pytest test",
  "custom exceptions in Python", "logging in Python".
metadata:
  exo-pack: python
  exo-execution: inline
  exo-permissions: write-code
---

# python-patterns

## Result

- Python code and tests that follow the project's own conventions first and these defaults second: typed public functions, specific exceptions, module-level loggers, resources closed with `with`, and a pytest test for each behavior.
- The project's format, lint, type and test commands ran, each named with its result; or, when you could not run one, the exact command and what you checked by hand instead.
- In the design phase: the decisions that `sdd-design` writes into design.md (where each module goes, its data shapes, its errors, its test layout). This skill writes no artifact of its own.

## When

| Moment | What you do |
|---|---|
| design, as the stack router (`.exo/shared/phase-skill-map.md`) | Decide modules, data shapes, errors and test layout with Structure, Typing and Errors below |
| apply, as the stack router | Write code and tests with every section below |
| On request | Someone asks how to write, structure or type Python code |

- **Not for:** reviewing a diff (skill:python-reviewer); deciding which tests a change needs (skill:test-strategy); a dependency audit (Route, below).
- **Precedence:** `.exo/context.md` (Commands, Conventions) and the neighboring code win over the defaults here. When the project does something differently on purpose (no type hints in tests, `black` instead of `ruff format`), follow it and do not "fix" it in passing.

## Route

Load the skill that fits the task, as `.exo/shared/skill-resolver.md` says, and read it in full:

| Task | Skill |
|---|---|
| Review a Python diff: someone asks for a review, or before a PR | skill:python-reviewer |
| A dependency, `requirements*.txt` or a lockfile (`uv.lock`, `poetry.lock`, `pdm.lock`) changes | skill:security-scan-jkp (pack `java`, which also covers Python) |
| Choose the tests and write test-spec.md | skill:test-strategy |
| Untrusted input, secrets, authentication or authorization in the code | skill:secure-coding-baseline |
| The full review of a change in verify | skill:harness-review |

- **A skill that is not installed degrades.** Say the sentence `<pack>/<skill> not installed — applying inline criteria`, apply the inline criteria of `.exo/shared/phase-skill-map.md` (last table), and record it. For `security-scan-jkp` on a Python project, that means `pip-audit` or OSV-Scanner on the lockfile or requirements, only if the project has them.
- **During apply,** your own diff is checked by `pre-commit-review` before each commit and by verify afterwards. Load skill:python-reviewer only when the person asks for a review.

## 1. Know the project

Before writing code, read:

1. `.exo/context.md`: Commands (format, lint, type check, test), Conventions, areas. When it does not exist, the README, `pyproject.toml` and the CI workflow give the commands.
2. `pyproject.toml`: `requires-python`, dependencies, `[tool.ruff]`, `[tool.mypy]` or `[tool.pyright]`, `[tool.pytest.ini_options]`; or `setup.cfg`, `requirements*.txt`, `tox.ini`.
3. The package manager from its lockfile: `uv.lock` (uv), `poetry.lock` (Poetry), `pdm.lock` (PDM), `requirements*.txt` (pip).
4. The layout (`src/<package>/` or a flat package) and two or three neighboring modules of the one you will touch: naming, docstrings, error handling, logging and how tests are laid out.

**Never use a feature above `requires-python`:**

| Feature | Needs |
|---|---|
| `X \| None`, `match`, `zip(strict=True)`, parenthesized context managers | 3.10 |
| `Self`, `StrEnum`, `ExceptionGroup` and `except*`, `asyncio.TaskGroup`, `tomllib`, `datetime.UTC` | 3.11 |
| The `type` statement, `@override`, generic syntax `def f[T](x: T)` | 3.12 |

Below the floor, use `typing_extensions` only if the project already depends on it.

## 2. Idioms

Write the Python the neighbors write. The defaults, with their anti-patterns, are in `references/idioms.md`:

- `pathlib.Path` for paths; `read_text(encoding="utf-8")` with an explicit encoding.
- Comprehensions for simple transforms; a plain loop when there is a side effect or more than one condition.
- `enumerate`, `zip`, unpacking, `any` and `all` instead of index arithmetic.
- `dataclasses` (`frozen=True` for values) or the project's model library (pydantic, attrs) for records; never bare dicts passed across modules.
- `Decimal` for money, never `float`; timezone-aware `datetime` (`datetime.now(timezone.utc)`).
- No mutable default arguments: `def f(items: list[str] | None = None)`.
- `is None` and `is not None`; do not rely on truthiness when `0` or `""` are valid values.
- Generators for large or streamed data; `functools.cache` only on pure functions.

## 3. Style

- PEP 8 as the project's formatter and linter enforce it (`ruff format` and `ruff check`, or `black` with `flake8`). Their config wins over PEP 8 on line length and import order.
- Names: `snake_case` functions and modules, `PascalCase` classes, `UPPER_CASE` constants, a leading `_` for what is private to the module.
- A docstring (PEP 257) on every public module, class and function: one line on what it does, then what is not obvious from the signature.
- Format only the lines you change. Reformatting a whole file hides the change in the diff.

## 4. Typing

Details and examples in `references/typing.md`.

- Annotate every public function, method and module-level constant. Let locals infer.
- Accept abstract types (`Iterable`, `Sequence`, `Mapping` from `collections.abc`), return concrete ones (`list`, `dict`).
- `X | None` for optional values (with `from __future__ import annotations` on 3.9 code bases); `Literal` for closed sets of strings; `TypedDict` or a dataclass for structured dicts; `Protocol` for duck-typed collaborators.
- No `Any` unless the value really is arbitrary. `cast()` and `# type: ignore[<code>]` only with a comment that says why.
- Imports needed only for types go under `if TYPE_CHECKING:`; that also breaks import cycles.
- Run the project's type checker (`mypy`, `pyright`) when it has one; do not add one without the person's approval.

## 5. Structure

- **Layout:** follow the existing one. For a new package, the `src/` layout with `pyproject.toml` (PEP 621).
- **Layers:** entry points (CLI, HTTP routes, consumers) parse input and call the domain; the domain is plain Python without framework imports; storage and external clients sit behind small interfaces. Dependencies point inward.
- **Modules:** one concept per module. A module that grows past a few hundred lines or imports from every layer is two modules.
- **`__init__.py`:** short; re-export only the public API, with `__all__` when the project uses it.
- **Import cycles:** move the shared piece to a lower module, or import for types under `TYPE_CHECKING`. Never hide a cycle with an import inside a function unless the project already does it for start-up time, with a comment.
- **Configuration:** read the environment once, in one settings object, at the entry point; pass it down.

## 6. Errors

- One base exception for the project or package (`class InvoiceError(Exception)`), with specific subclasses for what callers handle differently (`NotFoundError`, `ValidationError`).
- Raise the most specific exception, with a message that says what failed and with which value (never a secret or personal data).
- Chain causes: `raise StorageError("cannot save invoice 42") from exc`.
- Catch only what you can handle, as narrowly as possible. A bare `except:` or `except Exception: pass` is never acceptable; `except Exception` belongs only at a boundary (a request handler, a worker loop, `main`) that logs and converts.
- Translate at the boundary: domain errors become HTTP responses in the API layer (a FastAPI exception handler, a Django middleware) or an exit code and one `error:` line in a CLI.
- `contextlib.suppress(FileNotFoundError)` when ignoring an error is intended; say why in a comment.

## 7. Logging

- `logger = logging.getLogger(__name__)` per module. Configure handlers only at the entry point.
- No `print` outside CLI output meant for the person.
- Lazy arguments: `logger.info("invoice %s issued", number)`, not f-strings, so the message is built only when emitted.
- `logger.exception(...)` inside `except` to keep the traceback; log once, where the error is handled, not at every level.
- Never log secrets, tokens, full request bodies or personal data (`.exo/shared/data-protection.md`); log identifiers instead.

## 8. Resources and concurrency

- `with` for files, locks, database sessions, network connections and temporary directories.
- Every outbound network call has a timeout.
- In `async def` code, no blocking calls (sync HTTP clients, `time.sleep`, sync database drivers): use the async client, or run the blocking call in a thread (`asyncio.to_thread`). In FastAPI, a route that only does blocking I/O can be a plain `def`.
- Keep a reference to every task you create, and await or cancel it.

## 9. Tests with pytest

Conventions in `references/pytest.md`.

- One test per behavior, named for it: `test_complete_unknown_task_raises_key_error`. The scenarios of the spec map to tests by name when the change has a test-spec.md.
- Follow the project's layout (`tests/` mirroring the package, or tests next to the code), its fixtures (`conftest.py`) and its markers.
- `tmp_path` for files, `monkeypatch` for environment and attributes, `pytest.mark.parametrize` for cases of one rule, `pytest.raises(..., match=...)` for errors.
- No network, no real clock, no sleeps, no order between tests: inject the clock and the clients.
- Write the test first when the project declares strict TDD (`.exo/context.md`), and see it fail.

## 10. Run the checks

Run, in this order, the commands of `.exo/context.md` (or, without it, of the README and the CI workflow): format, lint, type check, tests (for example `ruff format --check .`, `ruff check .`, `mypy src`, `python -m pytest`, or the same through `uv run`). Report each exact command with its result.

- **Never install** a tool or a package the project does not have; never change its config to make a check pass.
- **When you cannot run a command** (no shell permission, no interpreter, no virtual environment): say so, give the exact command you would run, and check by hand what it would check: imports resolve, names exist, every new test asserts the behavior, no unused imports. Never claim a check passed if it did not run.

## Return

After the code, a short report:

```text
Python: 3.10 floor, src/ layout, ruff + mypy + pytest (from .exo/context.md).
Changed: src/toy_todo/export.py (new), src/toy_todo/cli.py, tests/test_export.py (new).
Checks: ruff check . passed; mypy src passed; python -m pytest: 9 passed.
Not run: none.
Next: python-reviewer when you want a review of the diff.
```

When a check could not run, the `Checks` line says `not run (no shell): python -m pytest` and the `Not run` line says what you verified by hand.

## Record

Inside an SDD change, the phase that loaded this skill records it; inline, before the phase envelope (`.exo/shared/capability-attribution.md`). A subagent lists it in its envelope notes and the orchestrator records it:

```bash
exo change record <change> --add capabilities_used '{"name": "python-patterns", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"python-patterns"'
```

In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Before you finish

- [ ] You read `.exo/context.md`, `pyproject.toml` and the neighboring code before writing.
- [ ] Nothing uses a feature above `requires-python` or a package the project does not have.
- [ ] Public functions are typed; no new `Any`, bare `except:` or mutable default.
- [ ] Errors are specific and chained; loggers are per module and log no secrets or personal data.
- [ ] Every new behavior has a pytest test that would fail without it.
- [ ] Each check ran with its exact command, or is listed as not run with what you checked by hand.
- [ ] Only the lines the task needs changed.
