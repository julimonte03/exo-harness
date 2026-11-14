# Project rules

This project uses a governed development engine. The configuration and the skill registry live in the repo's engine folder; the skills live in your agent's skills folder.

## Always

- **Evidence:** read the actual code and the full data chain before claiming anything. Cite `path:line`.
- **Scope:** do only what was asked. Do not refactor outside the scope or delete other people's `TODO`s.
- **Destructive commands:** ask for confirmation before deleting, overwriting or rewriting history.
- **Protected branches** (`main`, `master`, `prod`, `production`): never push directly, never use `--force` or `--no-verify`.
- **Commits:** Conventional Commits. If the project has a ticket pattern (`tickets.pattern` in the engine config), the user confirms the ticket; do not infer it from the branch.
- **Secrets:** never write credentials, tokens or personal data in code, commits or memory.

## Engine tools

They run from the terminal with the `exo` command, always with `--json` when you need to process the output.

- `exo change list` and `exo change status [<change>]`: status of the changes in progress.
- `exo change new <slug>` and `exo change record <change>`: create a change and keep its AI Usage Record.
- `exo fitness classify --evidence-json '<json>' --change <change>`: risk of a change (tier 1–4).
- `exo speclint <path>`, `exo specs list|merge` and `exo check`: artifacts, living specs and the checks before a PR.
- `exo skills list` and `exo doctor`: available skills, and diagnostics when something does not work.

## Changes (spec-driven)

If the project has the `sdd` pack, any change beyond a trivial fix goes through the SDD cycle: `/sdd-new <what you want>` starts it, `/sdd-continue` runs the next phase, `/sdd-ff` drafts the whole plan, `/sdd-status` shows where each change is.

- **Tier first:** each change is classified 1–4 and its phases follow the tier. An unknown tier is Tier 4; lowering a tier needs the person's literal confirmation.
- **Living specs:** approved behavior lives in `specs/capabilities/`; each change writes a delta that is merged when it is archived.
- **Before the PR:** `exo check` passes.

## Memory

You have a persistent memory, owned by the user, in `exo mem`. Use it without being asked:

- **At session start:** run `exo mem context` and read it before investigating from scratch.
- **Before solving something:** `exo mem search "<text>"` returns previews; get the details with `exo mem get <id>`.
- **When you decide, fix a bug or discover something non-obvious:** `exo mem save --type decision --title "…" --content "…"` (or `bugfix`, `discovery`, `gotcha`, `convention`). With a stable `--topic-key`, you update instead of duplicating.
- **When closing the session or before the context is compacted:** `exo mem session summary --content "<what was done and what is left>"`.
- **Never save secrets or personal data:** memory does not filter them and can be exported.

## If your agent has no subagents

Skills that ask for a "fresh context" or for delegation run inline: say so explicitly in your answer ("no isolation").
