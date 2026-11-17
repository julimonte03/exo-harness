---
name: sdd-spec
description: >-
  Writes the spec.md of an SDD change as a delta over the living specs: finds
  the capability, adds, modifies or removes requirements by ID with
  Given/When/Then scenarios, and checks it with exo speclint; in Tier 2 it
  also writes test-spec.md. Use it after sdd-new in Tier 2 or after
  sdd-propose in Tier 3 and 4, or when someone asks "sdd spec", "write the
  spec", "spec this change", "acceptance criteria", "requirements and
  scenarios".
metadata:
  exo-pack: sdd
  exo-execution: inline
  exo-phase: spec
  exo-permissions: write-specs
---

# sdd-spec

## Result

- `<change-root>/spec.md`, a delta from `.exo/shared/templates/spec.md` with `## ADDED Requirements`, `## MODIFIED Requirements` and `## REMOVED Requirements`, passing `exo speclint <change-root>` and `exo specs merge <change> --dry-run`.
- In Tier 2 only: `<change-root>/test-spec.md`, from `.exo/shared/templates/test-spec.md`. In Tier 3 and 4, `sdd-tasks` writes it.
- In Tier 3 and 4: the findings of `judge-product`, each one fixed or dismissed by the person.
- The person's answer at the approval gate, and the envelope of `.exo/shared/sdd-phase-common.md`, section D.

This skill never touches `<specs_dir>/capabilities/` (only `exo specs merge`, run by `sdd-archive`, changes the living specs), `proposal.md`, `exploration.md`, `design.md`, `tasks.md` or code.

## Inputs

- `exo change status <change> --json`: the change root and the tier (missing or unreadable means Tier 4).
- `proposal.md`: Scope is what the spec must cover; Out of Scope is what it must not. `exploration.md` when it exists: Current Behavior and Affected Capabilities.
- If an earlier artifact is wrong or lacks what you need, stop with `needs-input` and say what is wrong; do not edit it.
- An existing `spec.md` (drafted by `skill:sdd-new` in Tier 1 before the tier went up): start from it, complete it, and say so in the notes.

## Load the skills

Follow `.exo/shared/sdd-phase-common.md`, section A, at most 5 skills. Spec has no Required skill.

- **Tier 2:** `test-strategy`, for `test-spec.md` (step 5).
- **The change has a UI:** `accessibility-audit`. While the frontend pack is not installed, say `frontend/accessibility-audit not installed — applying inline criteria` and turn the criteria into requirements: for the UI that changes, keyboard access, visible focus, labels and accessible names, contrast and text alternatives (WCAG 2.2 AA), as an NFR or as scenarios.
- **A new user flow:** `product-discovery`. While the product pack is not installed, say `product/product-discovery not installed — applying inline criteria`: check that the Intent of `proposal.md` states the user, the problem, the value and how success is measured. If any is missing, stop with `needs-input`; never edit the proposal.
- **Tier 3 and 4:** the judge `judge-product` (step 6).

## Steps

### 1. Find the capability

- `exo specs list --json` lists each capability with its `path` and counts (`functional`, `non_functional`, `removed`, `problems`).
- Pick the capability whose Purpose covers the behavior and read its `spec.md` in full, including `## Removed Requirements`.
- One delta can touch several capabilities: each requirement ID names its own.
- No capability fits: use a new kebab-case noun (`payment-refunds`); `exo specs merge` creates its `spec.md` at archive. If two capabilities could own the behavior, ask the person.
- A capability with `problems` above 0: report them (`exo speclint <path>`) and do not fix them in this phase.

### 2. Number the requirements

- IDs are `CAP-<capability>-FR-n` (functional) or `CAP-<capability>-NFR-n` (non-functional: performance, security, accessibility, availability).
- **A new requirement takes the next free number of its capability:** the highest number of that kind in `## Requirements` and in `## Removed Requirements`, plus one. With FR-1 to FR-4 present and FR-5 removed, the next is FR-6; several new ones continue FR-7, FR-8.
- **A removed ID is never reused.** MODIFIED and REMOVED always point to an ID that exists in the living spec.

### 3. Write the delta

```markdown
## ADDED Requirements

### CAP-auth-FR-6: Lock the account after repeated failures
The system SHALL lock an account for 15 minutes after 5 failed sign-in attempts in a row.

#### Scenario S-1: The fifth failure locks the account
- Given an account with 4 failed sign-in attempts in a row
- When the fifth attempt fails
- Then the account is locked for 15 minutes
- And the person sees when they can try again

## REMOVED Requirements

### CAP-auth-FR-2: Unlimited sign-in retries
Reason: replaced by CAP-auth-FR-6.
```

- **ADDED:** one observable behavior per requirement, written as "The system SHALL ...". An FR needs at least one scenario; an NFR needs a measurable threshold, and a scenario when it can be tested that way.
- **MODIFIED:** the **full new text** of the requirement with **all its scenarios**, not just what changes: the merge replaces the whole block. The ID stays; the title may change.
- **REMOVED:** the heading and a `Reason:` line. No scenarios.
- **Scenarios:** `#### Scenario S-n: <title>` followed by `- Given`, `- When` and `- Then` lines (`- And` is fine). `S-n` is unique in the change and numbered from `S-1` across the whole delta, so `design.md` and `test-spec.md` can cite it. Cover the main path, the failure paths and the edge cases the proposal names.
- Keep only the sections you need, with at least one requirement in total. Describe behavior, not implementation: no class names, tables or SQL.
- Every Scope bullet of the proposal is covered by a requirement; nothing from Out of Scope appears.

### 4. Check

- `exo speclint <change-root>`: the format of every artifact, plus cross-references.
- `exo specs merge <change> --dry-run`: shows what the merge would do and fails on a MODIFIED or REMOVED ID that does not exist, or an ADDED ID that exists with other text. It writes nothing.

Fix until both pass.

### 5. `test-spec.md` (Tier 2 only)

Load `test-strategy` and write the three sections of the template:

- **Scope:** what is tested, at which levels (unit, integration, end to end).
- **Test Cases:** one row per case: `T-n`, what it covers (the `S-n` and the full requirement ID), level, description, and the exact command from `.exo/context.md`.
- **Traceability:** every requirement ID and every `S-n` of the delta, with the cases that cover it. Every scenario has at least one case.

Cite full IDs (`CAP-auth-FR-6`, `S-1`): speclint checks them against `spec.md` and the living specs. Run `exo speclint <change-root>` again.

### 6. Judge (Tier 3 and 4)

`judge-product` runs as a **separate read-only delegation to `sdd-judge`**, with the paths of `spec.md` and `proposal.md`, the first free `JPRD` ID from `exo change followups <change> --status all`, and a `## Skills to load before work` block with its `SKILL.md` path and, when installed, `product-discovery`. While the quality pack is not installed, say `quality/judge-product not installed — applying inline criteria` and put the criteria in the prompt: in a separate read-only pass, check that the change solves the problem in the proposal for its user, and nothing else; report gaps as findings. Without subagents, run it inline as its own pass after the spec is done and say "no isolation" (`.exo/shared/agent-capabilities.md`).

Record each finding with `exo change record <change> --followup '<json>'` (`.exo/shared/judge-common.md`, section F) and show it; the person decides to fix it (you edit the spec, check again and mark it with `--fixed <id>`) or to dismiss it (`dismissed_followups`, with its `id` and the reason).

### 7. Approval gate

Show the requirements added, modified and removed, the scenarios, the test cases (Tier 2) and the judge's findings.

- **Interactive** (default): ask "Adjust anything or continue?" and wait. On adjustments, edit your artifacts, check again and ask again.
- **Automatic:** continue, but stop on `needs-input` or `blocked` (`.exo/shared/sdd-phase-common.md`, section H).

## Record

```bash
exo change record <change> --add capabilities_used '{"name": "sdd-spec", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add capabilities_used '{"name": "test-strategy", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"sdd-spec"'
exo change record <change> --add knowledge_used '{"source": "docs", "ref": "specs/capabilities/auth/spec.md"}'
exo change record <change> --add judges_invoked '{"name": "judge-product", "result": "no gaps"}'
```

- Add each skill you loaded (`skills_used` too), each degraded one with `"resolution": "none"` and the degradation sentence as `note`, `sdd-judge` as a subagent when it ran, and `dismissed_followups` for the findings the person dismissed (`.exo/shared/capability-attribution.md`).
- In `hybrid` and `memory` persistence, save `spec.md` and `test-spec.md` with topic keys `sdd/<change-name>/spec` and `sdd/<change-name>/test-spec`, and update the state artifact in every mode (`.exo/shared/memory-convention.md`).

## Envelope

```yaml
status: ok
phase: spec
change_name: PROJ-123-add-login
artifacts:
  - path: specs/PROJ-123-add-login/spec.md
    summary: 1 requirement added (CAP-auth-FR-6), 1 removed (CAP-auth-FR-2); S-1 to S-3
  - path: specs/PROJ-123-add-login/test-spec.md
    summary: 4 test cases covering S-1 to S-3
notes: >-
  Isolation: no isolation (inline). Skills: sdd-spec (fallback-registry),
  test-strategy (fallback-registry). Degraded: none.
next: apply
```

- `next`: `apply` in Tier 1 and 2, `design` in Tier 3 and 4.
- `needs-input`: the proposal is missing what the spec needs, or the capability is unclear.
- `fitness_signal`: if a requirement reveals more risk than the tier says (sensitive data, an irreversible step), add it; only the orchestrator re-classifies.
