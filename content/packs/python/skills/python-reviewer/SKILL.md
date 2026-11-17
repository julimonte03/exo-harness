---
name: python-reviewer
description: >-
  Reviews a Python diff, read-only: correctness, type hints, exceptions,
  resource handling, security (SQL and command injection, unsafe
  deserialization, subprocess, path traversal, secrets, weak randomness),
  async pitfalls, performance and tests. Every finding has a severity, its
  path:line, a rule ID from a stable checklist and a fix as text, and the
  review ends with a verdict line. Runs the project's linter and type checker
  only when the project has them, and says what it checked by hand when it
  cannot run them. Use it when someone asks for a review of Python code, a
  branch or a pull request, or before opening a PR on a Python project; in
  SDD verify its Critical and High findings go to Issues Found. Not for
  writing code. Triggers: "review this Python code", "review my Python
  changes", "Python code review", "review the staged diff", "is this Python
  code safe", "review this PR before merge", "find bugs in this Python
  change".
metadata:
  exo-pack: python
  exo-execution: inline
  exo-permissions: read-only
---

# python-reviewer

## Result

A review of the Python files a diff touches: a findings table ordered by severity, each finding with its `path:line`, what is wrong, its rule ID from `references/checklist.md` (with the CWE when it is a security finding) and a fix as text; the tools that ran and the ones that could not; what was not reviewed; and a last line `Verdict: approve` or `Verdict: request changes`. You change nothing.

## When

- Someone asks for a review of Python code: the staged or uncommitted changes, a branch, a pull request, or files they name.
- Before opening a PR on a Python project, when the person wants a stack-specific review.
- In SDD verify, as a stack complement to skill:harness-review, when the stack router or the person asks for it.
- **Not for:** writing or fixing code (skill:python-patterns, after the review); the quick check before each commit (`pre-commit-review`, pack `quality`); a dependency audit (skill:security-scan-jkp); the full review of a change with its gates (skill:harness-review and skill:security-code-review).

## Permissions

- **Read-only.** Read and search files; run read-only git (`git diff`, `git diff --cached`, `git log`, `git show`, `git status`).
- Run only the lint, type and test commands of `.exo/context.md`, of the delegation or of the project's CI, and only if the project has the tool. Never install a tool or a package, never run a formatter or a linter in fix mode, never edit, stage, stash or commit.
- Never copy a secret or personal data into a finding: point at `path:line` and say what kind of data it is (`.exo/shared/data-protection.md`).

## Steps

1. **Scope.** Find the diff: `git diff --cached --stat` for staged changes, `git diff --stat` for unstaged ones, `git diff <target>...HEAD --stat` for a branch. Review the Python files (`*.py`, `*.pyi`) and what they need: `pyproject.toml` and requirements when they change, tests, config files that the code reads.
2. **Context.** Read `.exo/context.md` (commands, conventions), `requires-python` and the tool config in `pyproject.toml`. In an SDD change, also the spec and, when present, design.md and tasks.md: a scenario without a test is a finding.
3. **Whole files.** Read each changed file in full, not only its hunks. Follow every new input (request, CLI argument, file, environment, message) to where it is used (query, command, path, deserializer, template, log), one call into callers and callees when the flow leaves the file.
4. **Tools, when the project has them.** `ruff check`, `mypy` or `pyright`, `bandit`, and the tests, with the exact commands of `.exo/context.md` (or, without it, of the README and the CI workflow). Report each command with its result. When you cannot run them (no tool, no shell permission), give the exact command and review those points by hand; never report a tool result you did not see.
5. **Walk the checklist** below, category by category, with `references/checklist.md`.
6. **Confirm** each finding (Confirm before reporting), rate it (Severity) and write the fix as text.
7. **Return** the review (Return).

## What to look for

| Category | Look for | Rule IDs |
|---|---|---|
| Correctness | Wrong results, off-by-one, mutable defaults, late-binding closures, `float` for money, naive datetimes, iterators consumed twice, features above `requires-python` | PY-COR |
| Types | Untyped public functions, `Any` where the shape is known, `cast` or `# type: ignore` without reason, `None` not handled | PY-TYPE |
| Exceptions | Bare `except:`, `except Exception: pass`, lost causes (`raise` without `from`), `try` blocks too wide, `return` in `finally`, errors as control flow | PY-EXC |
| Resources | Files, sessions, connections or locks without `with`; outbound calls without a timeout; temporary files left behind | PY-RES |
| Security | SQL or shell built with strings, `shell=True` with input, `eval` or `exec`, `pickle` or `yaml.load` on untrusted data, path traversal, SSRF, `random` for tokens, weak hashes for passwords, secrets in code or logs, `assert` as a check, TLS verification off, debug mode | PY-SEC |
| Async | Blocking calls inside `async def`, coroutines never awaited, tasks without a reference | PY-ASYNC |
| Performance | Queries in loops (N+1), quadratic loops over large data, whole files in memory, string `+=` in loops | PY-PERF |
| Style | Departures from the project's formatter and linter config, `print` in library code, unclear names, dead code, missing docstrings on public API | PY-STYLE |
| Tests | New behavior without a test, tests that cannot fail, network or real time in tests, order-dependent tests | PY-TEST |

Each ID (`PY-SEC-1`, `PY-EXC-2`) is defined in `references/checklist.md` with its signals, what is not a finding, and the CWE for security items.

## Confirm before reporting

- **Evidence:** a finding names what happens, where (`path:line`) and why it is wrong. For security, the source of the input, the sink and the missing control; "could be unsafe" without a path from input to sink is not a finding.
- **Framework protections count:** the ORM's bound parameters, the template engine's autoescape, FastAPI's request validation, Django's CSRF middleware. No finding unless the diff bypasses them (`text()` with an f-string, `mark_safe`, `csrf_exempt`).
- **The project's conventions count:** a style the linter config allows is not a finding.
- **In scope:** what the diff adds or changes, and old code the diff now reaches. A problem that exists without the diff goes under Follow-ups, not in the table.
- **Unsettled:** when the control may live where you cannot see it (a gateway, another service), start the finding with `Unconfirmed:` and say what would settle it.

## Severity

The levels of `.exo/shared/judge-common.md`, section D, read for a Python diff:

| Severity | Examples |
|---|---|
| Critical | Injection reachable from input (SQL, shell, `eval`); untrusted data into `pickle` or unsafe YAML; a real secret in the diff; data loss or corruption in the main flow |
| High | Wrong result in the main flow; an error swallowed on the main path, so a failure looks like success; a session or connection leaked per request; an outbound call without a timeout in a request path; path traversal behind sign-in; new behavior with no test at all |
| Medium | An edge case or error path wrong; a mutable default; a broad `except` outside a boundary; `Any` on a public API; N+1 queries; a missing test for an edge case |
| Low | Style, naming, docstrings, an idiom that would read better |

Never raise or lower a severity to reach a verdict; the person decides what to fix.

## Verdict

- `Verdict: approve` when no finding is Critical or High.
- `Verdict: request changes` when one is, or when part of the diff that matters could not be reviewed (generated code, a file too large): say what under Not reviewed.

## Return

```markdown
# Python review: staged diff (3 files)

Tools: ruff check src tests: not run (no shell permission); checked by hand for unused imports and names. mypy: not configured.

| # | Severity | path:line | Finding | Rule | Fix |
|---|---|---|---|---|---|
| 1 | Critical | src/invoices/reports/aging.py:18 | The status from the query string is formatted into the SQL text, so a caller can change the query | PY-SEC-1 (CWE-89) | Bind it: `text("... WHERE status = :status")` with `{"status": status}` |
| 2 | High | src/invoices/reports/aging.py:31 | A bare `except:` returns an empty report on any error, including a lost database connection, so failures look like "no overdue invoices" | PY-EXC-1 | Catch the specific error you expect, log it, and let the rest propagate |
| 3 | Medium | src/invoices/reports/aging.py:9 | `buckets: list = []` is a mutable default shared between calls | PY-COR-1 | Default to `None` and create the list inside |
| 4 | High | tests/ | The new report has no test | PY-TEST-1 | Add tests for each bucket boundary and for an unknown status |

## Not reviewed

None.

## Follow-ups

- src/invoices/storage/repositories.py:61 (not in the diff): the invoice number count is not locked, so two concurrent issues can get the same number.

Verdict: request changes
```

- Order the table by severity, Critical first. Number the rows; IDs are the checklist rule IDs, not finding numbers.
- `path:line` points at the line that shows the problem; a whole-file finding (no test) points at the file or folder.
- Keep fixes as text or a one-line snippet; never rewrite the code for the person.

## In an SDD change

- **Verify:** it runs where the verify runs (`sdd-verifier`, read-only, in fresh context, or the session that runs the verify). Each Critical and High finding goes to Issues Found of `verify-record.md`, which `sdd-verify` writes, with its severity, `path:line`, impact and fix. This skill writes no gate and no file.
- **Before the PR** (`branch-pr`): the same review on `git diff <target>...HEAD`; the person decides each finding.
- **Judges** (`judge-code-reviewer`, `judge-security`) may reuse these rule IDs in their findings.

## Record

Inline, before the phase envelope (`.exo/shared/capability-attribution.md`); in a subagent, list it in the envelope notes and the orchestrator records it:

```bash
exo change record <change> --add capabilities_used '{"name": "python-reviewer", "type": "skill", "activation": "requested", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"python-reviewer"'
```

`activation` is `requested` when the person asked for the review and `auto` when the stack router or a phase loaded it. Findings the person decides not to fix go to `dismissed_followups` with their reason, recorded by the orchestrator; never dismiss one yourself. In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Before you finish

- [ ] Every changed Python file was read in full, and each new input was followed to its use.
- [ ] Each finding has a severity, `path:line`, a rule ID (and a CWE for security) and a fix as text.
- [ ] Tools ran only if the project has them; the commands that could not run are named, with what you checked by hand.
- [ ] Nothing outside the diff is in the table; it is under Follow-ups.
- [ ] No secret or personal data is copied into the review.
- [ ] No file was changed, staged or committed.
- [ ] The last line is `Verdict: approve` or `Verdict: request changes`.
