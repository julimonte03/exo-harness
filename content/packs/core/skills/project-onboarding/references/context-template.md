# Structure of .exo/context.md

The project profile that `project-onboarding` writes. Replace the example values with the project's real ones; delete the lines that do not apply. Every fact has its evidence (`path:line`) or is marked `(unverified)`.

```markdown
# Project context

## Stack

- Language: Python 3.12 (.python-version:1)
- Framework: FastAPI 0.115 (pyproject.toml:14)
- Package manager: uv (uv.lock)
- Storage: PostgreSQL 16 (docker-compose.yml:8)
- CI: GitHub Actions (.github/workflows/ci.yml)

## Commands

- Install: `uv sync`
- Test: `uv run pytest -q` (run on 2026-11-14: 212 passed, 0 failed, 38 s)
- Test one file: `uv run pytest tests/test_orders.py -q`
- Lint: `uv run ruff check .`
- Format: `uv run ruff format .`
- Build: `docker build -t orders .` (not run)

## Conventions

- TDD: strict
- Default branch: main. Branches: `<type>/<change-name>`.
- Commits: Conventional Commits (git log)
- Tests: in tests/, one file per module, named test_<module>.py (tests/)
- Errors: domain errors subclass AppError (src/errors.py:5)

## Areas

| Area | Path | What it does | Owner |
|---|---|---|---|
| API | src/api/ | HTTP endpoints | team-orders (CODEOWNERS:3) |
| Billing | src/billing/ | Invoices and totals | (unverified) |

## Risks

- src/billing/ handles money and has no integration tests.
- tests/test_sync.py is flaky on CI (memory 812).
- Credentials come from the environment (src/config.py:12); never hard-code them.

Last reviewed: 2026-11-14 at 3f2a9c1
```

## Notes

- **Stack:** languages and versions, frameworks, the package manager, storage and external services, CI.
- **Commands:** exact, copyable commands. The test command says when it was last run and with what result.
- **Conventions:** the `TDD:` line (`strict` or `not required`), branches, commits, code style, test layout, error handling.
- **Areas:** each area with its path, what it does and its owner, from `CODEOWNERS` or from the person.
- **Risks:** what can break or hurt: untested code, sensitive data, generated code, flaky tests, known incidents.
- **Last reviewed:** the last line, with the date and the short commit (`git rev-parse --short HEAD`).
