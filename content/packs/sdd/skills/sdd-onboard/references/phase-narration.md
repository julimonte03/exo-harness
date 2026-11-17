# Phase narration

Short texts to narrate the tour. Say them in your own words, in the person's language, and adapt them to the change at hand: name its real files, IDs and results. Each phase has what it does, what it leaves, why it exists, and what to point out once it ran.

## The map

- Every change goes through phases, and its **risk tier** (1 to 4) decides which ones. A typo fix and a payment flow do not deserve the same ceremony.
- **Tier 1:** risk, new (a short proposal), apply, a light verify, archive. **Tier 2** adds the spec and its test spec. **Tier 3** adds explore when needed, propose, design and tasks, plus advisory judges. **Tier 4** adds a final human review, `judgment-day`.
- Every artifact lives in one folder, `<specs_dir>/<change-name>/`, next to an AI Usage Record that says which skills and decisions took part.
- Before the PR, `exo check` verifies that the artifacts the tier requires are there and valid.
- The full map is `.exo/shared/phase-skill-map.md`; the shared rules of every phase are `.exo/shared/sdd-phase-common.md`.

## risk (skill `risk-tiering`)

- **Does:** scores seven risk dimensions (blast radius, criticality, data sensitivity, reversibility, footprint, test gaps, compliance), each with evidence, and lets the rules pick the tier.
- **Leaves:** `fitness-assessment.json`, written by `exo fitness classify --change`.
- **Why:** the ceremony matches the risk, and missing evidence means Tier 4, never a convenient low tier.
- **Point out:** the evidence behind each score (`path:line`), and that only the person can confirm a lower tier.

## new (skill `sdd-new`)

- **Does:** names the change, creates its folder, and drafts the proposal; in Tier 1, also the spec delta when behavior changes.
- **Leaves:** the change folder with `ai-usage-record.json`, and `proposal.md` (Intent, Scope, Approach, Out of Scope).
- **Why:** writing down what is in and out of scope before coding is the cheapest review there is.
- **Point out:** Out of Scope: it is what lets the verify call extra code drift.

## spec (skill `sdd-spec`, Tier 2 and up)

- **Does:** writes the requirements as a delta over the living specs, each with Given/When/Then scenarios, and the test spec that maps them to test cases.
- **Leaves:** `spec.md` (requirement IDs `CAP-<capability>-FR-n`, scenarios `S-n`) and, in Tier 2, `test-spec.md`.
- **Why:** a scenario is a test written in words; the IDs link the spec to the design, the tests and the verify.
- **Point out:** one `S-n` and where it will reappear (the test name, the verify's Scenario Coverage).

## apply (skill `sdd-apply`)

- **Does:** implements exactly the frozen plan, tests first, and commits each work unit.
- **Leaves:** code, tests and commits; in Tier 3 and 4, the ticked boxes of `tasks.md`.
- **Why:** a frozen plan keeps the change reviewable, and anything outside it becomes a follow-up instead of a surprise in the PR.
- **Point out:** the failing test before the code (red, then green), and a follow-up the implementer noted instead of fixing on the way.

## verify (skill `sdd-verify`)

- **Does:** checks the change in a fresh context, against the spec and the plan, and runs the tests with the project's exact command.
- **Leaves:** `verify-record.md` with a Verdict (`ready`, `needs-rework` or `blocked`) and, from Tier 2, the review gates in `gates/`.
- **Why:** the context that wrote the code is the worst one to judge it.
- **Point out:** Scenario Coverage (each `S-n` with its passing test) and Out-of-Scope Drift.

## archive (skill `sdd-archive`, with `branch-pr`)

- **Does:** merges the spec delta into the living specs, moves the change to the archive, runs `exo check`, and prepares the PR description.
- **Leaves:** updated `<specs_dir>/capabilities/`, the change under `<specs_dir>/archive/`, and `pr.md`.
- **Why:** the living specs describe the system as it is now, so the next change starts from the truth.
- **Point out:** the merged requirement in the living spec, and that the push and the PR wait for the person.

## Skipped phases

Say these where the phase would have run, and why this change does not need it.

| Phase | What it would do and leave | Why a small change skips it |
|---|---|---|
| explore (`sdd-explore`) | reads the area and compares approaches; `exploration.md` | the area is known and small |
| propose (`sdd-propose`) | refines the proposal with alternatives; `proposal.md` | the proposal from `sdd-new` is enough |
| design (`sdd-design`) | modules, data shapes, sequence, error handling and a Test Plan; `design.md`, plus a threat model from Tier 3 | one or two files do not need an architecture |
| tasks (`sdd-tasks`) | an ordered checklist of small tasks and a size forecast; `tasks.md` and `test-spec.md` | the proposal's Scope is already one work unit |
| judges | advisory reviews in separate read-only passes (security, code, product, business, frontend, team) | they start at Tier 3 |
| `judgment-day` | a final review in fresh context that the person approves | Tier 4 only |
| SPDD canvas | a seven-section contract the code is checked against, approved by a person (`.exo/shared/spdd-common.md`) | for Tier 3 and 4 domain logic, on request, or when the project requires it in the tier |

You may open the template of a skipped artifact (`.exo/shared/templates/design.md`, `canvas.md`) to show its sections. Never write the artifact itself.

## The recap

- What was built, in one sentence.
- Each artifact with its path and what it is for.
- The commands seen on the way: `exo change status <change>`, `exo speclint <change-root>`, `exo check --change <change>`.
- Next time: `/sdd-new <what you want>`, or ask for a new change; `/sdd-status` to see where a change stands.
