---
name: sdd-status
description: >-
  Reports where SDD changes are, without guessing: phase, tier and where the
  tier comes from, artifacts present and missing, open followups,
  inconsistencies and the next phase, all derived from exo change status and
  the status contract. Read-only. Use it when someone asks "sdd status",
  "/sdd-status", "where is this change", "what is missing", "what's next",
  "which changes are open", or before resuming a change in a new session.
metadata:
  exo-pack: sdd
  exo-execution: inline
  exo-phase: status
  exo-permissions: read-only+record
---

# sdd-status

## Result

For one change, a short report built only from what the engine returns and the artifacts it points to:

```text
Change: PROJ-123-add-login (specs/PROJ-123-add-login) · ticket PROJ-123 · epic none
Phase: spec · Tier 2 (from fitness-assessment.json)
Artifacts: ai-usage-record.json, fitness-assessment.json, proposal.md, spec.md
Missing for Tier 2: test-spec.md
Followups: 0 open, 1 dismissed
Inconsistencies: none
Next: spec (test-spec.md is missing)
```

For several changes, one line per change: name, phase, tier, next. Then the envelope of `.exo/shared/sdd-phase-common.md`, section D.

This skill writes no artifact and fixes nothing it finds. Its only write is one line in the AI Usage Record (see Record).

## Rules

- **Derive, never guess** (`.exo/shared/sdd-status-contract.md`). Every line of the report comes from a command output or from a file you read; if something cannot be derived, say so.
- Read the output of `exo change status`; do not re-derive the phase or the tier by listing folders by hand.
- If `exo` is not available or fails, say so and stop. Do not make up a status.

## Steps

### 1. Pick the change

- **Named:** `exo change status <change> --json`.
- **Not named:** `exo change status --json` returns every active change with its tier. With archived changes too: `exo change list --json` (`--no-archived` skips `archive/`).
- If the person means "this change" and there are several active ones, show the list and ask which one.
- If the command says the change does not exist or is ambiguous, show its message and the list.

### 2. Read the state

From `exo change status <change> --json`:

| Field | Use |
|---|---|
| `name`, `epic`, `path`, `ticket_key` | identify the change and its root |
| `phase` | the last artifact present (`new`, `risk`, `explore`, `propose`, `spec`, `design`, `tasks`, `apply`, `verify`, `archived`) |
| `tier`, `tier_source` | `assessment`: read from `fitness-assessment.json`. `missing`: no assessment yet, so Tier 3 applies until risk runs. `unreadable`: the file is broken, Tier 3 applies, report it |
| `artifacts` | the files present |
| `followups` | counts of `open`, `fixed` and `dismissed` |
| `warnings` | unreadable JSON files: each one is an inconsistency |

Never present a `missing` or `unreadable` tier as a real tier: write "Tier 3 (no assessment)" or "Tier 3 (unreadable assessment)".

### 3. Followups

If `followups.open` is above 0: `exo change followups <change> --json` and list each open one. Use `--status dismissed` or `--status all` when the person asks for the rest.

### 4. Missing artifacts

Compare `artifacts` with the mandatory artifacts of the tier (`.exo/shared/sdd-phase-common.md`, section C): Tier 1 `proposal.md`, and `spec.md` only if the change alters behavior; Tier 2 adds `spec.md` and `test-spec.md`; Tier 3 adds `design.md` and `tasks.md`. Every tier also needs `ai-usage-record.json` and `fitness-assessment.json`. Before a PR, `exo check --change <change>` is the authoritative check.

### 5. Next phase

`exo change status <change> --json` returns `next_phase` and `next_reason`, computed with the rules of `.exo/shared/sdd-status-contract.md`, Next phase. Report them as they are; do not re-derive them. An archived change has `next_phase: none`.

### 6. The anchor

If the change root has `context-anchor.md`, read its Now and Open questions (skill:context-anchoring) and add one line to the report: `Anchor: next step <step> (<who>); <n> open questions`. A next step that the engine contradicts (a phase already done, or another next phase) is an inconsistency. Never update the anchor here.

### 7. Inconsistencies

Report them; do not resolve them by guessing:

- an artifact of a later phase without an earlier one the tier requires (`design.md` without `spec.md` in Tier 3);
- a `change_name` in the record (`exo change ai-usage <change> --json`, field `record.change_name`) that differs from the folder `name`;
- a Verdict `ready` with open followups;
- every entry in `warnings`, and a `tier_source` of `unreadable`.

For each: the file, what is wrong, and either a question for the person or the phase that owns the file and should fix it.

### 8. Memory

With `sdd.persistence` `memory` or `hybrid` (`.exo/config.json`), also read the state artifact as `.exo/shared/memory-convention.md` says: `exo mem search "<change-name> state" --json`, pick the observation with topic key `sdd/<change-name>/state`, then `exo mem get <id> --json`. Never work from the preview.

- `hybrid`: if memory and the files disagree, the files win; say that they disagree.
- `memory`: the documents live only in memory, so the files show at most the JSON records and `phase` stops early. Take the phase from the state artifact and say where it came from.
- `none`: only the conversation has the documents; say so.

## Record

Only for one active change the person asked about by name (`/sdd-status`):

```bash
exo change record <change> --add capabilities_used '{"name": "sdd-status", "type": "skill", "activation": "requested", "resolution": "fallback-registry"}'
```

Record nothing for the overview of several changes, for archived changes, or when the record is unreadable (report it instead). When the orchestrator uses this skill, it records its own work.

## Envelope

```yaml
status: ok
phase: status
change_name: PROJ-123-add-login
artifacts: []
notes: >-
  Isolation: no isolation (inline). Skills: sdd-status (fallback-registry).
  Tier 2 from fitness-assessment.json. Inconsistencies: none.
next: spec
```

- For an overview of several changes: `change_name: none` and `next: none`; the table already has the next phase of each.
- `needs-input`: the change is ambiguous, or an inconsistency needs the person.
- `blocked`: `exo` is not available.
