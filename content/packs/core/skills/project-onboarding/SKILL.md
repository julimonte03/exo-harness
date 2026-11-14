---
name: project-onboarding
description: >-
  Refines the project profile after `exo init`: the stack, the build, test and
  lint commands (running the tests once to verify them), the conventions, the
  areas and their owners, and the known risks. Confirms them with the person,
  writes .exo/context.md and saves a short summary to memory. Use it right
  after installing the engine, when .exo/context.md is missing or stale, or
  when the stack, the commands or the owners change. Triggers: "onboard this
  project", "set up the project context", "write context.md", "refresh the
  project profile", "update the project wiki".
metadata:
  exo-pack: core
  exo-execution: inline
---

# project-onboarding

## Result

`.exo/context.md` describes the project as it is today, and the person confirmed it. It has the sections Stack, Commands, Conventions, Areas and Risks, and ends with a `Last reviewed:` line with the date and the commit. Its test command was run once. A short summary is in memory under the topic key `project/context`.

`.exo/context.md` is the project wiki that the agents and the SDD cycle read (`.exo/shared/project-wiki-guard.md`). The engine never generates or overwrites it: this skill writes it with the person's approval, and the person owns it.

## Before you start

1. **The engine is installed:** `.exo/config.json` exists. If it does not, the person runs `exo init` first. If something about the installation looks wrong, run `exo doctor`.
2. **First time or refresh:** if `.exo/context.md` already exists, read it. Keep what the person wrote and change only what is outdated.
3. **Memory:** `exo mem search "project context" --json`, then `exo mem get <id> --json` for the observation whose topic key is `project/context`, if there is one. Never work from a preview.

## Gather the evidence

Read before writing, and cite `path:line` for every fact (skill:context-retrieval).

| Section | Where to look |
|---|---|
| Stack | manifests and lockfiles (`package.json`, `pyproject.toml`, `pom.xml`, `build.gradle`, `go.mod`, `Cargo.toml`), runtime version files (`.nvmrc`, `.python-version`), Dockerfiles |
| Commands | manifest scripts, `Makefile`, CI workflows, README. What CI runs wins over what the README says. |
| Conventions | linter and formatter configs, contributing guides, existing agent rules, the test layout and naming, `git log --oneline -20` for the commit style |
| Areas | the top-level folders and modules; `CODEOWNERS` for the owners |
| Risks | code without tests, code that handles money, credentials or personal data, generated or vendored code, flaky tests, incidents in memory |

- **4 or more files:** when the agent has subagents, delegate the reading to a read-only explorer (`sdd-explorer` when the sdd pack is installed) and work from its findings. Without subagents, read in small batches and summarize as you go.
- **No secrets in the profile.** Write where a secret comes from (for example "the API key comes from the environment, `src/config.py:12`"), never its value. No personal data.

## Verify the commands

- Run the test command once. Write down the result: passed and failed counts, and how long it took. Pre-existing failures go to Risks; do not fix them here.
- If the tests need services (a database, the network) or take more than a few minutes, ask the person before running them.
- Run the build and lint commands only if they are quick and change nothing; otherwise mark them `(not run)`.
- A command or fact you could not confirm is written with `(unverified)`.

## Confirm with the person

Show the draft and ask only what the repository cannot tell you, in the person's language:

- "Are these the commands you use to build, test and lint?"
- "Who owns each area?" (when there is no `CODEOWNERS`)
- "Does the team practice strict TDD, writing each test first and seeing it fail?"
- "Is there a risky area or a known problem I should add?"

Write what they confirmed and what you verified; everything else stays `(unverified)`.

## Write .exo/context.md

- Follow the structure in `references/context-template.md`: Stack, Commands, Conventions, Areas, Risks, and the `Last reviewed:` line.
- Commands are exact and copyable. Under Conventions, write `TDD: strict` or `TDD: not required`, as the person said: skill:test-strategy and skill:code-generation read that line.
- The last line is `Last reviewed: <YYYY-MM-DD> at <commit>`, with today's date and the output of `git rev-parse --short HEAD`.
- Keep it short, a page or two. Link to the docs instead of copying them.
- In a refresh, show the person what changes before writing it.
- Commit it as its own unit when the person agrees (skill:work-unit-commits), for example `docs: add project context`.

## Save to memory

```bash
exo mem save --type convention --topic-key project/context --title "Project context" \
  --content "Stack: Python 3.12, FastAPI. Test: uv run pytest -q. Lint: uv run ruff check . Conventions: Conventional Commits, TDD strict. Risks: src/billing has no integration tests."
```

- 5 to 10 lines: what an agent needs at the start of a session, with the real values.
- The same topic key updates the observation instead of duplicating it.
- Never secrets or personal data (skill:memory-protocol).

## Tickets

If `tickets.pattern` in `.exo/config.json` is null but the team uses tickets (IDs in `git log` or in branch names, or the person says so), suggest the command and let the person decide:

```bash
exo init --ticket-pattern '[A-Z][A-Z0-9]*-\d+' --ticket-example 'PROJ-123'
```

- Adapt the regular expression to their IDs, for example `'#\d+'` with the example `'#123'`.
- The pattern is the person's decision: never run it without their go-ahead.

## Finish

Tell the person what was written, what is still `(unverified)`, and when to refresh the profile: when the stack, the commands, the conventions or the owners change, or when a change finds the wiki stale (`.exo/shared/project-wiki-guard.md`).
