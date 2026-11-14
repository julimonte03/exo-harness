# SDD status contract

How the state of a change is derived. The rule is: **derive it from the artifacts and the records, never guess it.** `exo change status [<change>] --json` reports the phase, the tier with its source (`assessment`, `missing` or `unreadable`) and the artifacts. The `sdd-status` skill and the orchestrator derive the next phase from that output with the rules below.

## Where a change is

- **Active:** `<specs_dir>/[<epic>/]<change-name>/`. An epic is a folder without change artifacts that holds changes.
- **Archived:** `<specs_dir>/archive/[<epic>/]YYYY-MM-DD-<change-name>/`.
- **Not changes:** `capabilities/` (the living specs), and folders starting with `.` or `_`.

## Phase

The phase is set by the **last artifact present**, in this order:

| Artifact | Phase |
|---|---|
| (only `ai-usage-record.json`, or nothing) | `new` |
| `fitness-assessment.json` | `risk` |
| `exploration.md` | `explore` |
| `proposal.md` | `propose` |
| `spec.md` | `spec` |
| `design.md` | `design` |
| `tasks.md` | `tasks`; `apply` once any box is checked |
| `verify-record.md` | `verify` |
| (in `archive/`) | `archived` |

## Tier

From `fitness-assessment.json` (`exo fitness classify --change`). If it is missing or unreadable, the tier is unknown and **Tier 4** applies. Never assume a lower tier.

## Next phase

Take the phases of the tier (`.exo/shared/phase-skill-map.md`, Phases per tier) and pick the first one whose output is missing:

1. no `fitness-assessment.json` → risk;
2. no `proposal.md` → new;
3. Tier 3 and 4: the proposal's Approach says "The area is unknown: explore before proposing." and there is no `exploration.md` → explore; `sdd-propose` is not yet in the record (`skills_used` or `capabilities_used`) → propose;
4. Tier ≥ 2 without `spec.md` → spec; Tier 2 without `test-spec.md` → spec;
5. Tier 3 and 4 without `design.md` → design; without `tasks.md` or `test-spec.md` → tasks;
6. apply: in Tier 3 and 4, unchecked boxes in `tasks.md`; in Tier 1 and 2, `sdd-apply` is not yet in the record;
7. no `verify-record.md`, or its Verdict is `needs-rework` → verify (after fixing);
8. Tier 4 and `judges_invoked` has no `{"name": "judgment-day", "result": "approved"}` → judgment;
9. Verdict `ready` and no open followups → archive.

The record conventions (`sdd-propose`, `sdd-apply`, the `judgment-day` result) are in `.exo/shared/capability-attribution.md`.

## Inconsistencies

Report them, do not resolve them by guessing:

- an artifact of a later phase without the earlier one the tier requires (for example `design.md` without `spec.md` in Tier 3);
- a `change_name` in `ai-usage-record.json` that does not match the folder;
- a Verdict `ready` with open followups (`exo change followups <change>`);
- an unreadable JSON file (it shows up in `warnings`).

Say which file and what is wrong, and ask the person, or fix it in the phase that owns the file.

## Memory

With `hybrid` persistence, also read the state artifact (`.exo/shared/memory-convention.md`); if memory and the files disagree, the files win: say that they disagree. With `memory` persistence there are no files: take the phase and the artifacts from the state artifact and the artifacts saved in memory.
