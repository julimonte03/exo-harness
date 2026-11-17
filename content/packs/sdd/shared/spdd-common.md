# SPDD contract

Structured prompt-driven development (SPDD) is an optional overlay on the SDD cycle: before the code, a REASONS Canvas fixes what the code will do, how and under which limits; a person approves it; and the code and the canvas stay in sync until the change is archived. These rules bind `reasons-canvas-author`, `prompt-spec-review` and `prompt-code-sync`, and the phase skills that call them. When a skill and this contract disagree, this contract wins.

## A. When SPDD applies

Use the overlay when **any** of these holds:

- **Tier 3 or 4 with domain logic worth fixing before the code:** business rules, calculations, state machines, permissions, money, or integrations whose contract matters;
- **the person asks for it**, at any tier; or
- **the project requires it:** `governance.gates` in `.exo/config.json` lists `prompt_spec_review` for the change's tier. Then every change of that tier has a canvas and its gate, whatever its content: the exclusions and the doubt rule below do not apply.

Do not use it for configuration, copy, styling, dependency bumps, or pure refactors with no behavior change. When in doubt in an interactive run, ask the person; in an unattended run, skip it and say so in the phase notes. Record the choice once in the AI Usage Record: `--add decisions '{"summary": "SPDD canvas: yes (Tier 3, pricing rules)", "by": "agent"}'`.

## B. The canvas

- **File:** `<change-root>/canvas.md`, started from `.exo/shared/templates/canvas.md`. `exo speclint` requires its seven sections, none empty.
- **Written after** `design.md`, in the design phase, by `reasons-canvas-author`. The canvas does not replace the design: it is the contract the code is checked against. In Tier 1 or 2 there is no design phase: the orchestrator's session writes it right before apply, from the proposal and the spec, and asks for its approval (section C).

| Section | What it holds | Checked in verify |
|---|---|---|
| Requirements | The requirement IDs (`CAP-<cap>-FR-n`) and scenarios (`S-n`) the change covers, in the spec's words | Every one is implemented |
| Entities | The domain objects, their fields and invariants | The code keeps the invariants |
| Approach | The chosen solution and why it beats the alternatives | — |
| Structure | The files and modules to create or change, and their dependencies | No code outside them |
| Operations | The steps the code performs, numbered, unhappy paths included | One-to-one with the code |
| Norms | The conventions: naming, errors, logging, tests, project rules | The code follows them |
| Safeguards | What must never happen: security and data limits, invariants, bounds, the threats of the threat model | Each one holds |

- **IDs it cites must exist** in the delta or the living specs: `exo speclint` checks them.
- **Never copy secrets or personal data** into the canvas; name the kind of data and where it lives.

## C. Who does what

| Phase | Skill | Does |
|---|---|---|
| design (Tier 3 and 4) | `reasons-canvas-author` | Writes `canvas.md` from the spec, `design.md` and the threat model |
| design (Tier 3 and 4) | `prompt-spec-review` (approval mode) | Checks the canvas is complete and coherent with the spec and the design, shows it to the person, and writes `gates/prompt_spec_review.md` with their decision |
| before apply (Tier 1 and 2) | `reasons-canvas-author`, then `prompt-spec-review` (approval mode) | The same two steps, in the orchestrator's session, from the proposal and the spec |
| apply | `prompt-code-sync` | Before each task, reads the Operations and Safeguards it implements; keeps canvas and code in sync (section D) |
| apply, after a logic correction | `prompt-spec-review` (approval mode) | Shows the changed canvas to the person and rewrites the gate with their decision, before the code changes |
| verify | `prompt-spec-review` (conformance mode) | Checks the diff one-to-one against Operations, Norms and Safeguards, looks for scope creep, and rewrites the gate with the result |

The skills of the overlay ship in the `sdd` pack with the phase skills, so they are never missing: a missing one is an incomplete install (`.exo/shared/sdd-phase-common.md`, section A).

## D. Keeping canvas and code in sync

- **Logic correction** (the behavior must change: a rule was wrong, a case was missing): change the canvas **first**, show the person the change in the canvas, then change the code. A logic correction after the gate was APPROVED sends the gate back to approval: `prompt-spec-review` runs again in approval mode before the code changes.
- **Refactoring** (same behavior, different code): change the code **first**, then update Structure, and Operations if the steps moved. No new approval is needed.
- **Never let them drift.** When the code cannot follow the canvas, stop the task and return `status: needs-input` with the conflict. Do not silently change either side.
- **A correction that changes what spec.md requires or what design.md decides** goes to that phase first; the canvas follows it.
- **In `sdd-implementer`** (a subagent), never edit canvas.md: return the exact edit in the envelope. The orchestrator's session applies it, shows it to the person and records it. A refactor edit comes with `status: ok` and needs no approval; a logic correction comes with `status: needs-input`, and apply is delegated again only after `prompt-spec-review` gets the person's approval of the changed canvas.
- Record each sync as a decision: `--add decisions '{"summary": "Canvas: logic correction in Operations 3 (rounding)", "by": "agent"}'`.

## E. The gate

- **Name and file:** `prompt_spec_review`, `<change-root>/gates/prompt_spec_review.md`, from `.exo/shared/templates/gate.md`. It is a conditional gate: `exo check` requires it whenever `canvas.md` exists, at any tier.
- **Approval mode** (design; before apply in Tier 1 and 2; after a logic correction): `APPROVED` only when the person explicitly approves the canvas; their words go in the gate's Findings or Approval notes. Without that approval (unattended run, or the person asks for changes), `ESCALATED`, with `Requires tech_lead approval: yes`.
- **Conformance mode (verify):** rewrite the gate with the design approval and the conformance result. Conformance cannot approve a canvas nobody approved: without an APPROVED design approval, the verdict stays `ESCALATED`. With an approved canvas, `ESCALATED` when a gap is Critical or High or a changed file is outside Structure, and `APPROVED` otherwise. Every gap is listed with `path:line` and the canvas section it breaks; the Medium and Low ones also go to `verify-record.md`, Issues Found, and do not block. A canvas edited after the design approval is a gap only when the edit changes logic without a new approval: the refactor edits recorded as decisions (`Canvas: refactor…`, section D) need none.
- A gate written in a read-only subagent comes back as text, and the orchestrator writes it verbatim.

## F. Recording

- Each overlay skill in `capabilities_used` (`.exo/shared/capability-attribution.md`).
- The conformance gaps the person decides not to fix go to `dismissed_followups`, with the skill as `judge` and the canvas item as `rule`; never dismiss one on your own:

  ```bash
  exo change record <change> --add dismissed_followups '{"judge": "prompt-spec-review", "rule": "Operations 4", "reason": "the person keeps the negative total for credit notes until the billing change of next quarter"}'
  ```
