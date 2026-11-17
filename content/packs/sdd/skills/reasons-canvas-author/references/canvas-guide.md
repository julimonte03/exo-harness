# Canvas guide

How to fill each section of `canvas.md` and how to check it before the approval. The contract is `.exo/shared/spdd-common.md`, section B; the template is `.exo/shared/templates/canvas.md`.

## What the canvas is for

The canvas is the contract the code is checked against: in apply, `prompt-code-sync` holds each task to it; in verify, `prompt-spec-review` checks the diff against it one item at a time. Write every item so that a reviewer who has only the canvas and the diff can say "holds" or "does not hold".

## Section by section

### Requirements

- One bullet per ADDED or MODIFIED requirement of the delta: the full ID (`CAP-billing-FR-4`), one line in the spec's words, and its scenarios (`S-2`, `S-3`) with a few words each.
- REMOVED requirements: one bullet each, `CAP-billing-FR-2 (removed): <what disappears>`. The verify checks that the behavior is gone.
- Do not paraphrase in a way that changes the meaning. "Before today" and "on or before today" are different requirements.
- Nothing the spec does not have. A requirement the design implies but the spec lacks is a gap: `needs-input` for the spec phase.

### Entities

- The domain objects the change creates or touches: the type or table, its fields with their types and allowed values, and where it lives (`src/billing/invoice.py:12`, or `(new)`).
- **Invariants:** what is always true of the object ("`total` equals the sum of the lines minus the discount, never negative"). These are what the verify checks in the code.
- Data levels from `.exo/shared/data-protection.md` for fields with personal data or credentials: "`email`, Restricted".

### Approach

- Two to five lines: the solution design.md chose and the reason it beats each rejected alternative.
- No new alternatives and no new decisions: copy the reasoning of design.md and the proposal, shorter.

### Structure

- One bullet per file of design.md, Modules / Files: path, responsibility, and what it depends on.
- The direction of dependencies when it matters ("`cli.py` depends on `store.py`, never the reverse").
- End with "No other file changes." This line is the scope: a changed file outside the list is scope creep in verify.
- Tests are files too: list the test files the Test Plan names.

### Operations

- Numbered, in the order the code runs them. One observable action per step: what goes in, what the code does, what comes out or is stored.
- Each unhappy path of Error Handling is its own step: the condition, what the code does, what the user or caller sees, and what is not written.
- Each step ends with the scenario or threat it serves: `(S-2)`, `(TM-1)`. A step with neither is either glue (say so) or something the spec does not ask for.
- Concrete outputs: exact messages, exit codes, status codes, stored shapes. They are what tests assert.

### Norms

- Numbered conventions the code must follow, each one checkable in the diff: error style, logging (what is logged, at which level, what never), naming, test framework and style, typing, dependencies.
- Take them from `.exo/context.md`, the stack router, and the code itself, with the `path:line` of an existing example ("errors as one `error:` line and exit code 1, as in `src/app/cli.py:40`").
- Leave out what the linter already enforces.

### Safeguards

- Numbered "never" statements, each with its source:
  - each threat of the threat model: `Never ... (TM-2)`;
  - data limits: what never reaches logs, responses, memory or the model (`.exo/shared/data-protection.md`);
  - invariants whose breach would lose or corrupt data;
  - bounds: sizes, limits, timeouts.
- Each one checkable: name the place or the behavior a reviewer looks at.
- A threat that needs no Safeguard (its mitigation is outside the code, such as a gateway setting) still gets a line that says where it is mitigated.

## Coherence checklist

Before handing the canvas to `prompt-spec-review`, check:

| Check | How |
|---|---|
| Every requirement and scenario of the delta is in Requirements | Compare the IDs of spec.md with the bullets |
| Every `S-n` is served by at least one Operation | Look for `(S-n)` in Operations |
| Every Operation lands in a file of Structure | For each step, name the file |
| Every file of Structure serves an Operation or a test | No file without a reason |
| Structure matches design.md, Modules / Files | Same files, nothing extra |
| Every `TM-n` of the threat model is a Safeguard | Look for `(TM-n)` in Safeguards |
| Operations match Sequence Of Operations and Error Handling | Same steps and outcomes |
| Every Norm and Safeguard is checkable | A reviewer can point at the code that holds it |
| Entities match Data Shapes | Same fields, same allowed values |
| No secrets, personal data or real values | Kinds and locations only |
| `exo speclint <change-root>` passes | Run it |

## Common mistakes

- **Restating the spec in Operations.** Operations say how the code achieves the scenario, step by step, not the scenario again.
- **Vague Norms.** "Follow best practices" checks nothing. Name the practice and the example.
- **Missing unhappy paths.** If Error Handling lists three failures, Operations has three steps for them.
- **A Structure without the closing line.** Without "No other file changes." the verify cannot call anything scope creep.
- **Renumbering after approval.** It breaks every reference in the gate, the record and the sync decisions.
- **Deciding in the canvas.** A choice the design does not make goes to the person and to design.md first.
