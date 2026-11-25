---
name: reasons-canvas-author
description: >-
  Writes the REASONS canvas of an SDD change (canvas.md): the structured
  prompt that fixes what the code will do before any code exists, in seven
  sections (Requirements, Entities, Approach, Structure, Operations, Norms,
  Safeguards) drawn from the spec delta, design.md and the threat model. Part
  of the optional SPDD overlay: it runs in the design phase, after design.md
  (right before apply in Tier 1 and 2), for Tier 3 changes with domain
  logic worth fixing first (business rules, calculations, state machines,
  permissions, money, integration contracts), whenever the person asks for
  it, or when the project requires it in the tier. A section it cannot fill
  becomes a question for the person, never a guess. Use it when the person
  asks for a canvas, a structured prompt or a design contract before coding,
  or mentions SPDD. Triggers: "write the canvas", "REASONS canvas", "SPDD",
  "structured prompt for this change", "fix the rules before we code",
  "design contract for the code".
metadata:
  exo-pack: sdd
  exo-execution: inline
  exo-permissions: write-specs
---

# reasons-canvas-author

## Result

- `<change-root>/canvas.md`, started from `.exo/shared/templates/canvas.md`, with its seven sections in order and none empty. Every item comes from the spec, design.md, the threat model or the code (`path:line`).
- Every gap either answered by the person or written as an explicit open question in the section it belongs to.
- `exo speclint <change-root>` passes: the seven sections are there and filled, and every requirement and scenario ID the canvas cites exists.
- The canvas handed to skill:prompt-spec-review in approval mode, which writes the gate `prompt_spec_review`. This skill never writes the gate and never approves its own canvas.

The rules of the overlay are in `.exo/shared/spdd-common.md`. When this skill and that contract disagree, the contract wins.

## When

- **Only when the overlay applies** (`.exo/shared/spdd-common.md`, section A): Tier 3 with domain logic worth fixing before the code; the person asks for it, at any tier; or the tier lists `prompt_spec_review` in `governance.gates`, which makes the canvas mandatory there.
- **Not** for configuration, copy, styling, dependency bumps, or refactors with no behavior change, unless the tier requires the gate. When in doubt in an interactive run, ask once: "This change has <the rule or calculation>. Do you want a canvas? It adds your approval of the contract before any code." In an unattended run, skip it and say so in the phase notes.
- **In the design phase** (skill:sdd-design), in this order:
  1. design.md passes speclint, and the threat model is in Risks & Mitigations (Tier 3);
  2. this skill writes canvas.md;
  3. the design judges review design.md and canvas.md together (`.exo/shared/judge-common.md`, section C);
  4. skill:prompt-spec-review asks the person to approve the canvas;
  5. the design phase asks for its own approval.
- **Tier 1 and 2** have no design phase. When the overlay applies there, the orchestrator runs this skill in its session right before apply (skill:sdd-orchestrator, SPDD overlay): write the canvas from the proposal (Scope, Out of Scope) and spec.md, and read the code yourself for Structure and Norms. Say in the notes that there was no design.md to check against.
- **Again** when spec.md or design.md change after the canvas: update only the affected items. The changed canvas goes back to approval.
- **Not for a logic correction found in apply:** skill:prompt-code-sync writes that edit and sends it to approval (`.exo/shared/spdd-common.md`, section D).

## What it writes and what it never touches

- **Writes** only `<change-root>/canvas.md`, plus its memory mirror in `hybrid` and `memory` persistence (`.exo/shared/sdd-phase-common.md`, sections B and C).
- **Never touches** proposal.md, spec.md, design.md, the threat model, the gates or the code. If an earlier artifact is wrong or silent (a scenario without a clear Then, a file in design.md that contradicts the code, a threat without a mitigation), stop and return `status: needs-input` naming the file and the gap. The fix belongs to the phase that owns that file.
- **Adds no decision.** The canvas restates the design as a contract the code is checked against. A choice the design does not make is a question for the person and for design.md, not a line in the canvas.

## Before you start

1. Run `exo change status <change> --json` for the tier, the phase and the artifacts. An unknown tier is Tier 3.
2. spec.md and design.md exist (Tier 3) and `exo speclint <change-root>` passes. Otherwise return `needs-input`.
3. Read in full: spec.md; design.md, every section, with the `### Threat model` of Risks & Mitigations; proposal.md (Scope, Out of Scope); `gates/threat_model.md` when present; `.exo/context.md` (conventions, test command); and the living specs that the delta modifies (`<specs_dir>/capabilities/<capability>/spec.md`).
4. Read the code the change touches, for Entities and Norms. Read 1 to 3 files inline; for 4 or more, delegate the reading to `sdd-explorer` (`.exo/shared/sdd-phase-common.md`, section G).
5. If canvas.md already exists, update it. Never start over without saying so.

## Fill the seven sections

| Section | Take it from | Write it as |
|---|---|---|
| Requirements | spec.md: every ADDED and MODIFIED requirement and every `S-n`; REMOVED ones marked as removed | One bullet per requirement: its full ID, one line in the spec's words, and its scenarios |
| Entities | design.md, Data Shapes; the existing types in the code | Each domain object with its fields (type, allowed values) and its invariants; new or existing, with `path:line` |
| Approach | design.md, Architecture Overview; proposal.md, Approach | The chosen solution in two to five lines, and why it beats each alternative the design rejected |
| Structure | design.md, Modules / Files | Every file to create or change, its responsibility and the direction of its dependencies, ending with "No other file changes." |
| Operations | design.md, Sequence Of Operations and Error Handling | Numbered steps, one observable action each; each unhappy path is its own step; each step names the `S-n` or `TM-n` it serves |
| Norms | `.exo/context.md`, the stack router, the conventions the code already follows (`path:line`) | Numbered conventions the code must follow: naming, errors, logging, tests, project rules |
| Safeguards | the threat model (`TM-n`), Risks & Mitigations, `.exo/shared/data-protection.md`, the invariants | Numbered "never" statements, each with its source |

How to fill and check each section is in `references/canvas-guide.md`; a complete canvas is in `references/canvas-example.md`.

### Rules for every section

- **Numbered items** in Operations, Norms and Safeguards. The review and the sync cite them as "Operations 3" or "Safeguards 2", so never renumber an approved canvas: append new items, and mark a removed one `(removed)`.
- **Checkable.** Each item points to something a reviewer can find in the diff. "The code is clean" is not a Norm; "user errors print one line starting with `error:` and exit with 1" is.
- **IDs that exist.** Cite only requirement IDs and `S-n` defined in the delta or the living specs: speclint checks them. Threats are the `TM-n` of the threat model. Never invent an `S-n`, and never use `T-n`, which is a test case of test-spec.md.
- **No secrets and no personal data.** Name the kind of data and where it lives ("the customer's national ID, Restricted, in `customers.national_id`"), never a value. Examples are synthetic.
- **Coherent.** Every `S-n` of Requirements appears in at least one Operation; every Operation lands in a file of Structure; every `TM-n` of the threat model is a Safeguard, or the canvas says why not.

## Gaps

When a section cannot be filled from what exists:

- **Interactive:** ask the person in one message, at most three concrete questions at a time, each with the options you see. Write a clarifying answer (an error message, a convention, a bound) in the canvas. An answer that changes the design (a new step, a new file, a new rule) goes to design.md first, through skill:sdd-design, which owns it and runs in this same session; then the canvas follows.
- **Unattended,** or the person cannot answer now: write the item as an open question where it belongs, naming what it blocks:

```markdown
5. Open question: is the discount rounded per line or on the invoice total? (blocks S-4; the spec says "rounded to cents", the design does not say where)
```

An open question keeps speclint green but blocks the approval: skill:prompt-spec-review reports it as a gap. Return `status: needs-input` with the questions.

## Check

1. `exo speclint <change-root>` passes. Fix the errors in canvas.md; an error in another phase's file means `needs-input`.
2. Go through the coherence checklist in `references/canvas-guide.md`.
3. Hand over to skill:prompt-spec-review in approval mode, in the same session. Never write the gate, and never call the canvas approved.

## Record

Before the envelope of the phase (`.exo/shared/capability-attribution.md`). Record the overlay decision once per change (`.exo/shared/spdd-common.md`, section A): skip it if the record already has it, and use `"by": "human"` when the person asked for the overlay.

```bash
exo change record <change> --add decisions '{"summary": "SPDD canvas: yes (Tier 3, volume discount rules)", "by": "agent"}'
exo change record <change> --add capabilities_used '{"name": "reasons-canvas-author", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"reasons-canvas-author"'
```

- `activation` is `requested` when the person asked for the canvas by name.
- In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).
- In `hybrid` and `memory` persistence, save the canvas with the topic key `sdd/<change-name>/canvas` (`.exo/shared/memory-convention.md`).

## Return

This skill runs inside a phase, usually design, and that phase's envelope reports it (`.exo/shared/sdd-phase-common.md`, section D):

```yaml
artifacts:
  - path: specs/add-volume-discount/canvas.md
    summary: "Canvas: 2 requirements, 4 scenarios, 6 operations, 4 norms, 4 safeguards, no open questions"
notes: >-
  SPDD: yes (Tier 3, volume discount rules). Skills: reasons-canvas-author (fallback-registry).
  Next: prompt-spec-review in approval mode.
```

With open questions left, the phase returns `status: needs-input` and lists them.

## Before you finish

- [ ] The overlay applies (`.exo/shared/spdd-common.md`, section A), and the decision is recorded once.
- [ ] Seven sections in order, none empty; Operations, Norms and Safeguards numbered.
- [ ] Every requirement and `S-n` of the delta is in Requirements and in at least one Operation.
- [ ] Structure lists every file of Modules / Files and ends with "No other file changes."
- [ ] Every `TM-n` of the threat model is a Safeguard.
- [ ] No decision that design.md does not make; no secret, personal data or real value.
- [ ] `exo speclint <change-root>` passes.
- [ ] Gaps asked or written as open questions; the canvas handed to skill:prompt-spec-review; no gate written here.
