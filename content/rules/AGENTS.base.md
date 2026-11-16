# Project rules

This project uses a governed development engine. Its configuration (`config.json`), the skill registry and the shared contracts live in the repo's `.exo/` folder; the skills live in your agent's skills folder. Answer in the person's language.

## Always

- **Evidence:** read the actual code and the full data chain before claiming anything. Use `context-retrieval` before the first search; cite `path:line` next to each claim and end with a `Sources:` line.
- **Scope:** do only what was asked. Do not refactor outside the scope or delete other people's `TODO`s.
- **Destructive commands:** ask for confirmation before deleting, overwriting, resetting or rewriting history.
- **Data protection:** never write credentials or tokens anywhere, never save personal data in memory, and keep it out of code, commits, prompts and external systems unless a waiver allows it (`.exo/shared/data-protection.md`).

## Git

- **Commits:** Conventional Commits (`<type>(<scope>): <summary>`). If the project has a ticket pattern (`tickets.pattern` in the config), the person confirms the ticket and it goes in a `Refs: <ticket>` footer; never infer it from the branch or from earlier commits. If the person confirms there is no ticket, commit without the footer.
- **Branches and PRs:** branch from the target branch with only this change's diff; everything goes through a PR with a conventional title; CI is green before you call it done.
- **Protected branches** (`governance.protected_branches` in the config): never push directly, never use `--force` or `--no-verify`.
- **Enforcement:** the engine's git hooks check messages, staged secrets and pushes, and CI runs `exo check`. A hook that blocks you is right: fix the cause. Never bypass it or force-push, even when asked: if the person decides to, they run that command themselves.

## Gates

- A gate always runs its skill and writes `<change-root>/gates/<gate>.md`. The gates per tier are `governance.gates` in the config.
- A gate that is not APPROVED, or whose Approval says yes, needs the `tech_lead` role. In an unattended run, do not stop: leave it as it is and say so.
- Judges advise: they propose followups and never change the work (`.exo/shared/judge-common.md`).

## Engine tools

Run them from the terminal, with `--json` when you need to process the output.

- `exo change new|record|status|list`: changes and their AI Usage Record.
- `exo fitness classify --evidence-json '<json>' --change <change>`: risk tier 1–4 of a change.
- `exo speclint`, `exo specs list|merge`, `exo check`: artifacts, living specs and the checks before a PR.
- `exo gate publish`: one PR comment per gate (`.exo/shared/ci-and-review.md`).
- `exo skills list`, `exo doctor`, `exo p0`: skills, diagnostics and the minimum regression gate.

## Changes (spec-driven)

If the project has the `sdd` pack, any change beyond a trivial fix goes through the SDD cycle: `/sdd-new <what you want>` starts it, `/sdd-continue` runs the next phase, `/sdd-ff` drafts the whole plan, `/sdd-status` shows where each change is.

- **Tier first:** each change is classified 1–4 and its phases and gates follow the tier. An unknown tier is Tier 4; lowering a tier needs the person's literal confirmation.
- **Living specs:** approved behavior lives in `specs/capabilities/`; each change writes a delta that is merged when it is archived.
- **Before the PR:** `exo check --change <change>` and `exo check --base <target branch>` pass (only `--base` scans the diff for secrets); CI runs the second.

## Memory

You have a persistent memory, owned by the user, in `exo mem`; follow the `memory-protocol` skill and use it without being asked:

- **At session start:** `exo mem context`. **Before solving something:** `exo mem search "<text>"`, then `exo mem get <id>`.
- **When you decide, fix a bug or discover something non-obvious:** `exo mem save --type decision|bugfix|discovery|gotcha|convention --title "…" --content "…"`, with a stable `--topic-key` to update instead of duplicating.
- **Before closing or compacting:** `exo mem session summary --content "<what was done and what is left>"`.
- **Never save secrets or personal data:** memory does not filter them and can be exported.

## If your agent has no subagents

Skills that ask for a "fresh context" or for delegation run inline: say so explicitly in your answer ("no isolation").
