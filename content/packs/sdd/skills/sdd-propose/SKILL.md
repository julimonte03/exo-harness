---
name: sdd-propose
description: >-
  Refines the proposal.md of an SDD change, using the exploration: who the user
  is, the problem, the value and how success is measured, a concrete scope, the
  chosen approach with its alternatives, and what stays out of scope. In Tier 3
  and 4 it runs the product and business judges, then stops at an approval
  gate. Use it after sdd-explore, or when someone asks "sdd propose", "refine
  the proposal", "write the proposal", "what exactly are we building".
metadata:
  exo-pack: sdd
  exo-execution: inline
  exo-phase: propose
  exo-permissions: write-specs
---

# sdd-propose

## Result

- `<change-root>/proposal.md` refined, with its four sections (Intent, Scope, Approach, Out of Scope), passing `exo speclint <change-root>/proposal.md`.
- In Tier 3 and 4: the findings of `judge-product` and `judge-business`, each one fixed or dismissed by the person.
- The person's answer at the approval gate.
- The envelope of `.exo/shared/sdd-phase-common.md`, section D, with `next: spec`.

This skill edits only `proposal.md`, which `skill:sdd-new` drafted. It never touches `exploration.md`, `spec.md`, `design.md`, code, the living specs or the tier.

## Inputs

- `exo change status <change> --json`: the change root, `tier` and `tier_source` (missing or unreadable means Tier 4).
- `proposal.md`. If it does not exist, the change skipped the new phase: return `needs-input` and suggest `skill:sdd-new`.
- `exploration.md` when explore ran: its Options, Risks and Open Questions.
- `.exo/context.md`, and `exo specs list --json` for the capabilities the change touches.
- Read previous artifacts as `sdd.persistence` says (`.exo/shared/sdd-phase-common.md`, section B).

## Load the skills

Follow `.exo/shared/sdd-phase-common.md`, section A, at most 5 skills.

- **Required:** `context-retrieval`: retrieve context before claiming anything, and cite the source next to each claim.
- **Conditional:** `product-discovery`, for a new feature, an MVP or an unclear value. While the product pack is not installed, say `product/product-discovery not installed — applying inline criteria` and apply them: write who the user is, the problem, the value and how success is measured in the Intent, and ask the person when any of them is unclear.
- **Judges (Tier 3 and 4):** `judge-product` and `judge-business`, in step 4.

## Steps

### 1. Read

Read the inputs above. If `exploration.md` is wrong or missing something you need, stop and return `needs-input` with what is wrong: do not edit it.

### 2. Refine each section

- **Intent**, four short parts:

  ```markdown
  - **User:** branch tellers who reverse card payments.
  - **Problem:** a reversal takes three screens and four minutes, and 12% fail on timeout (src/reversals/flow.py:88).
  - **Value:** fewer failed reversals and shorter queues at the branch.
  - **Success measure:** 95% of reversals done in one screen in under a minute, measured in the reversal logs 30 days after release.
  ```

  The user is a role, not a person's name. The success measure is a number or an observable check, with when and where it is measured.
- **Scope:** bullets, each one something the person can verify. Name the capabilities the change touches.
- **Approach:** the chosen option from the exploration, by name, and why; each alternative in one line with why not. Say what will be hard to reverse, so design can record it. Cite `path:line` for the existing code it builds on. If you pick an option the exploration advised against, say why.
- **Out of Scope:** what this change does not do, including the options left for later. `None.` only if there is truly nothing.

Ask the person, in one message, what you cannot settle from the artifacts or the code. Never fill a gap with a guess.

### 3. Check

`exo speclint <change-root>/proposal.md`. Fix every error.

### 4. Judges (Tier 3 and 4)

Each judge is a **separate read-only delegation to `sdd-judge`**, never inside your own context (`.exo/shared/phase-skill-map.md`). Each prompt gives the change name and root, the paths of `proposal.md` and `exploration.md`, the person's request and `.exo/context.md` (the stage before a proposal, `.exo/shared/judge-common.md`, section C), the first free ID of the judge's prefix (`JPRD`, `JBIZ`) from `exo change followups <change> --status all`, and a `## Skills to load before work` block with the judge's `SKILL.md` path and, when installed, the skills it reuses (`product-discovery` for `judge-product`).

The judges ship in the quality pack. While it is not installed, say `quality/judge-product not installed — applying inline criteria` (and the same for `judge-business`), and put in the prompt, instead of a path, the judge's inline criteria from `.exo/shared/phase-skill-map.md` (Inline criteria for skills not installed), copied as they are.

Without subagents, run each judge inline after the proposal is done, as its own pass with its criteria, and say "no isolation" (`.exo/shared/agent-capabilities.md`).

Judges are advisory. Record each finding with `exo change record <change> --followup '<json>'` (`.exo/shared/judge-common.md`, section F) and show it; the person decides to fix it (you edit `proposal.md`, run speclint again and mark it with `--fixed <id>`) or to dismiss it (`dismissed_followups`, with its `id` and the reason).

### 5. Approval gate

Show the Intent, the Scope bullets, the chosen approach and the judges' findings with their outcome.

- **Interactive** (default): ask "Adjust anything or continue?" and wait. On adjustments, edit `proposal.md`, run speclint again and ask again.
- **Automatic:** continue, but stop on `needs-input` or `blocked` (`.exo/shared/sdd-phase-common.md`, section H).

## Record

```bash
exo change record <change> --add capabilities_used '{"name": "sdd-propose", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"sdd-propose"'
exo change record <change> --add capabilities_used '{"name": "judge-product", "type": "judge", "activation": "auto", "resolution": "none", "note": "quality/judge-product not installed — applying inline criteria"}'
exo change record <change> --add capabilities_used '{"name": "sdd-judge", "type": "subagent", "activation": "auto"}'
exo change record <change> --add judges_invoked '{"name": "judge-product", "result": "2 findings: 1 fixed, 1 dismissed"}'
exo change record <change> --add dismissed_followups '{"judge": "judge-business", "rule": "no cost estimate", "reason": "internal tool; cost covered by the team budget"}'
```

- `activation` is `requested` when the person asked for this skill by name. Record `judge-business` the same way as `judge-product`, plus each degraded conditional skill.
- The `sdd-propose` entry in `skills_used` is how `skill:sdd-status` knows that the proposal was refined.
- In `hybrid` and `memory` persistence, save the proposal with topic key `sdd/<change-name>/proposal`, and update the state artifact `sdd/<change-name>/state` in every mode (`.exo/shared/memory-convention.md`).

## Envelope

```yaml
status: ok
phase: propose
change_name: PROJ-123-add-login
artifacts:
  - path: specs/PROJ-123-add-login/proposal.md
    summary: Intent with success measure; Option B chosen; 2 items out of scope
notes: >-
  Isolation: no isolation (inline); judges ran as sdd-judge subagents.
  Skills: sdd-propose (fallback-registry), context-retrieval (fallback-registry).
  Degraded: judge-product, judge-business (quality not installed).
next: spec
```

- `needs-input`: the Intent or the scope needs the person, or an earlier artifact is wrong.
- `fitness_signal`: if refining the scope contradicts the tier, add it; only the orchestrator re-classifies.
