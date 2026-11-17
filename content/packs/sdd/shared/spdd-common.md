# SPDD contract

Structured prompt-driven development (SPDD) is an optional overlay on the SDD cycle: before the code, a REASONS Canvas fixes what the code will do, how and under which limits; a person approves it; and the code and the canvas stay in sync until the change is archived. These rules bind `reasons-canvas-author`, `prompt-spec-review` and `prompt-code-sync`, and the phase skills that call them. When a skill and this contract disagree, this contract wins.

## A. When SPDD applies

Use the overlay when **either** holds:

- **Tier 3 or 4 with domain logic worth fixing before the code:** business rules, calculations, state machines, permissions, money, or integrations whose contract matters; or
- **the person asks for it**, at any tier.

Do not use it for configuration, copy, styling, dependency bumps, or pure refactors with no behavior change. When in doubt in an interactive run, ask the person; in an unattended run, skip it and say so in the phase notes. Record the choice once in the AI Usage Record: `--add decisions '{"summary": "SPDD canvas: yes (Tier 3, pricing rules)", "by": "agent"}'`.

## B. The canvas

- **File:** `<change-root>/canvas.md`, started from `.exo/shared/templates/canvas.md`. `exo speclint` requires its seven sections, none empty.
- **Written after** `design.md`, in the design phase, by `reasons-canvas-author`. The canvas does not replace the design: it is the contract the code is checked against.

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
| design | `reasons-canvas-author` | Writes `canvas.md` from the spec, `design.md` and the threat model |
| design | `prompt-spec-review` (approval mode) | Checks the canvas is complete and coherent with the spec and the design, shows it to the person, and writes `gates/prompt_spec_review.md` with their decision |
| apply | `prompt-code-sync` | Before each task, reads the Operations and Safeguards it implements; keeps canvas and code in sync (section D) |
| verify | `prompt-spec-review` (conformance mode) | Checks the diff one-to-one against Operations, Norms and Safeguards, looks for scope creep, and rewrites the gate with the result |

The skills of the overlay ship in the `sdd` pack with the phase skills, so they are never missing: a missing one is an incomplete install (`.exo/shared/sdd-phase-common.md`, section A).

## D. Keeping canvas and code in sync

- **Logic correction** (the behavior must change: a rule was wrong, a case was missing): change the canvas **first**, show the person the change in the canvas, then change the code. A logic correction after the gate was APPROVED sends the gate back to approval: `prompt-spec-review` runs again in approval mode before the code changes.
- **Refactoring** (same behavior, different code): change the code **first**, then update Structure, and Operations if the steps moved. No new approval is needed.
- **Never let them drift.** When the code cannot follow the canvas, stop the task and return `status: needs-input` with the conflict. Do not silently change either side.
- Record each sync as a decision: `--add decisions '{"summary": "Canvas: logic correction in Operations 3 (rounding)", "by": "agent"}'`.

## E. The gate

- **Name and file:** `prompt_spec_review`, `<change-root>/gates/prompt_spec_review.md`, from `.exo/shared/templates/gate.md`. It is a conditional gate: `exo check` requires it whenever `canvas.md` exists, at any tier.
- **Approval mode (design):** `APPROVED` only when the person explicitly approves the canvas; their words go in the gate's Findings or Approval notes. Without that approval (unattended run, or the person asks for changes), `ESCALATED`, with `Requires tech_lead approval: yes`.
- **Conformance mode (verify):** rewrite the gate with the design approval and the conformance result. `APPROVED` when every Operation, Norm and Safeguard holds and nothing is outside Structure; `ESCALATED` when one does not hold, listing each gap with `path:line` and the canvas section it breaks.
- A gate written in a read-only subagent comes back as text, and the orchestrator writes it verbatim.

## F. Recording

- Each overlay skill in `capabilities_used` (`.exo/shared/capability-attribution.md`).
- The conformance gaps the person decides not to fix go to `dismissed_followups` with their reason; never dismiss one on your own.
