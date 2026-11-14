---
name: sdd-new
description: >-
  Starts an SDD change: checks the branch and the project wiki, names the
  change (asking once for a ticket and once for an epic when the project uses
  tickets), creates it with exo change new, classifies its risk, drafts
  proposal.md (plus the spec.md delta when a Tier 1 change alters behavior) and
  stops at an approval gate. Use it when someone wants to start a feature, a
  fix or any change through the SDD cycle, or says "sdd new", "/sdd-new", "new
  change", "start a change", "new feature", "plan this change".
metadata:
  exo-pack: sdd
  exo-execution: inline
  exo-phase: new
  exo-permissions: write-specs
---

# sdd-new

## Result

A change that is named, classified and ready for its next phase:

- `<specs_dir>/[<epic>/]<change-name>/` with `ai-usage-record.json`, created by `exo change new`.
- `fitness-assessment.json`, recorded by `skill:risk-tiering` through `exo fitness classify --change`.
- `proposal.md`, from `.exo/shared/templates/proposal.md`; minimal in Tier 1.
- `spec.md`, a delta from `.exo/shared/templates/spec.md`, **only in Tier 1 and only when the change alters behavior**. From Tier 2 on, the spec phase (`skill:sdd-spec`) owns `spec.md`.
- The person's answer at the approval gate.
- The envelope of `.exo/shared/sdd-phase-common.md`, section D, as the last thing in the answer.

This skill never writes code, tests, `exploration.md`, `design.md`, `tasks.md` or `test-spec.md`, never touches `<specs_dir>/capabilities/`, and never edits `ai-usage-record.json` or `fitness-assessment.json` by hand.

## Before you start

- Read `.exo/config.json`: `tickets.pattern`, `tickets.example`, `specs_dir`, `sdd.persistence` and `sdd.mode`.
- **Inside the orchestrator** (`sdd-orchestrator`), follow it: it may have run the wiki guard, created the change or recorded the tier already. `exo change status <change> --json` shows what exists (`artifacts`, `tier_source`); skip the steps that are done.
- **Called alone** (`/sdd-new`), run every step yourself.
- Load skills as `.exo/shared/sdd-phase-common.md`, section A, says. The phase map has no row for `new`: this skill uses `skill:risk-tiering` for its risk step and follows `skill:memory-protocol` and `ai-usage-record`.
- Persistence follows sections B and C of the same contract: with `hybrid` or `memory`, save each artifact with its topic key (`.exo/shared/memory-convention.md`).

## Steps

### 1. Wiki guard

Run the start checkpoint of `.exo/shared/project-wiki-guard.md`:

1. `git status` and `git branch --show-current`. On a protected branch (`governance.protected_branches`), propose a branch for the change before `exo change new` writes anything (`branch-pr`). Uncommitted work that is not part of this change: ask what to do with it.
2. With an upstream, `git status -sb`. If the branch is behind, say so and ask before going on.
3. No `.exo/context.md`: suggest `project-onboarding` first. Tier 1 can go on without it; if step 4 gives Tier 3 or 4, stop and ask the person whether to run `project-onboarding` before planning.
4. Read `.exo/context.md`. If the change touches an area it does not describe, or it contradicts the code, note it as a wiki update for the end of the change.

### 2. Name the change

- **Slug:** lowercase kebab-case, two to five words, verb first, from the request: "let users sign in with Google" becomes `add-google-sign-in`. Letters, digits and single hyphens only; no ticket in the slug.
- **Ticket**, only if `tickets.pattern` is not null. Ask once, with these words: "Is there a ticket for this change? It looks like `<tickets.example>`. Leave it empty if not." Never infer it from the branch, the commits or the conversation.
- **Epic**, only if `tickets.pattern` is not null. Ask once: "Does this change belong to an epic? Its ID looks like `<tickets.example>`. Leave it empty if not." Both questions can go in the same message.
- **No pattern:** ask nothing about tickets or epics.
- An empty answer means no ticket (or no epic).

### 3. Create the change

```bash
exo change new <slug> --ticket <ID> --epic <ID> --purpose '<one sentence: what the change is for>' --json
```

- Leave out `--ticket` and `--epic` when there is none. Pass the IDs exactly as the person wrote them: the command validates them against the pattern, normalizes them (`AB#123` becomes `AB-123`) and keeps the exact ID in the record.
- From the output, `name` is the change name and `path` is the change root. Never build the folder by hand.
- **The ticket is rejected:** say that it does not match and show `<tickets.example>`, then ask once more. If the second answer is rejected too, create the change without a ticket and say so in the envelope notes. Never invent an ID and never change the pattern.
- **The name exists:** ask whether to continue that change (`skill:sdd-status`) or choose another slug.

### 4. Classify the risk

Unless `exo change status <change> --json` already shows `tier_source: assessment`, run `skill:risk-tiering` for the change now. It records the tier and reports tier, rule and ceremony. A missing or unreadable assessment means Tier 4.

The tier decides what you draft:

| Tier | Draft now | Next phase |
|---|---|---|
| 1 | minimal `proposal.md`; `spec.md` only if behavior changes | apply |
| 2 | `proposal.md` | spec |
| 3, 4 | `proposal.md` | explore if the area is unknown, otherwise propose |

### 5. Draft `proposal.md`

Start from `.exo/shared/templates/proposal.md`. Fill all four sections; write `None.` instead of leaving one empty (speclint rejects empty sections).

- **Intent:** the problem, for whom, and why now.
- **Scope:** concrete bullets the person can check.
- **Approach:** the solution at a high level, with `path:line` for the existing code it builds on; alternatives in one line each.
- **Out of Scope:** what this change does not do.

Tier 1 keeps each section to one to three lines. In Tier 3 and 4, if the area is not understood yet, end Approach with "The area is unknown: explore before proposing." `skill:sdd-status` reads that sentence to send the change to explore.

Read the code before describing it: one to three files inline; four or more, delegate to `sdd-explorer` (`.exo/shared/sdd-phase-common.md`, section G). Without subagents, read in small batches (`.exo/shared/agent-capabilities.md`). Do not fill gaps with guesses: unknowns become questions at the gate.

### 6. Draft `spec.md` (Tier 1, behavior changes only)

A change alters behavior when a user, a caller or a test can observe the difference: output, API, UI, errors, stored data. A refactor, docs, or build and tooling work with the same behavior does not.

- **Behavior changes:** write the delta with the rules of `skill:sdd-spec` (capability from `exo specs list`, next free ID, scenarios `#### Scenario S-n: <title>` with Given, When and Then).
- **No behavior change:** write no `spec.md`, and add "No behavior change." to Scope. `exo check` reminds that the change must not alter behavior.

### 7. Check

`exo speclint <change-root>`. Fix every error before the gate.

### 8. Approval gate

Show a short summary: change name and path, ticket and epic, tier with rule and ceremony, the Intent in one line, the Scope bullets, the spec delta if any, open questions, and the next phase.

- **Interactive** (`sdd.mode: interactive`, the default): ask "Adjust anything or continue?" and wait. On adjustments, edit your own artifacts, run `exo speclint` again and ask again.
- **Automatic** (`sdd.mode: auto`, or the person asked for it): continue, but still stop on `needs-input`, `blocked` or a downgrade (`.exo/shared/sdd-phase-common.md`, section H).

### 9. Record

```bash
exo change record <change> --add capabilities_used '{"name": "sdd-new", "type": "skill", "activation": "requested", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"sdd-new"'
exo change record <change> --add knowledge_used '{"source": "code", "ref": "src/auth/login.py:42"}'
exo change record <change> --add decisions '{"summary": "Created without a ticket: the answer did not match the pattern twice", "by": "human"}'
```

- `activation` is `requested` when the person called `/sdd-new` or asked for it by name, `auto` when the orchestrator chose it. `resolution` says how you found this skill (`.exo/shared/skill-resolver.md`).
- Add `sdd-explorer` (`"type": "subagent"`) if you delegated, and a `knowledge_used` entry per source you cite. Record decisions only when there are any.
- `skill:risk-tiering` records its own entries. Details: `.exo/shared/capability-attribution.md`.
- Update the change's state artifact in memory (`sdd/<change-name>/state`, `.exo/shared/memory-convention.md`).

### 10. Continue

- **Inside the orchestrator:** return the envelope; the orchestrator decides what runs next.
- **Called alone:** when the person says to continue, load the skill of the next phase and run it: Tier 1 `sdd-apply`, Tier 2 `skill:sdd-spec`, Tier 3 and 4 `skill:sdd-explore` or `skill:sdd-propose`. For the whole cycle, suggest `sdd-orchestrator`.

## Envelope

```yaml
status: ok
phase: new
change_name: PROJ-123-add-login
artifacts:
  - path: specs/PROJ-123-add-login/proposal.md
    summary: minimal proposal, Tier 1 (FM-30)
  - path: specs/PROJ-123-add-login/spec.md
    summary: 1 requirement added (CAP-auth-FR-3)
notes: >-
  Isolation: no isolation (inline). Skills: sdd-new (fallback-registry),
  risk-tiering (fallback-registry). Degraded: none. Ticket: PROJ-123.
  wiki guard: branch feat/PROJ-123-add-login, up to date; context.md fresh.
next: apply
```

- `needs-input`: the person has to answer something (the ticket, an unknown in the proposal, onboarding in Tier 3 or 4). Say exactly what to ask.
- `blocked`: `exo` is not available, or you cannot write the change root.
- `fitness_signal`: if what you read while drafting contradicts the tier, add it; only the orchestrator re-classifies.
