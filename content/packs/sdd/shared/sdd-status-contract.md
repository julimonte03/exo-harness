# SDD status contract

How the state of a change is derived. The rule is: **derive it from the artifacts and the records, never guess it.** `exo change status [<change>] --json` applies these rules; the `sdd-status` skill and the orchestrator read its output instead of re-deriving it.

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
3. Tier 3 and 4 without `exploration.md` when the proposal says the area is unknown → explore; without the refined proposal → propose;
4. Tier ≥ 2 without `spec.md`, or without `test-spec.md` → spec (Tier 2) or tasks (Tier 3 and 4);
5. Tier 3 and 4 without `design.md` → design; without `tasks.md` → tasks;
6. unchecked boxes in `tasks.md`, or Tier 1 with code still to write → apply;
7. no `verify-record.md`, or its Verdict is `needs-rework` → verify (after fixing);
8. Tier 4 without an approved `judgment-day` → judgment;
9. Verdict `ready` → archive.

## Inconsistencies

Report them, do not resolve them by guessing:

- an artifact of a later phase without the earlier one the tier requires (for example `design.md` without `spec.md` in Tier 3);
- a `change_name` in `ai-usage-record.json` that does not match the folder;
- a Verdict `ready` with open followups (`exo change followups <change>`);
- an unreadable JSON file (it shows up in `warnings`).

Say which file and what is wrong, and ask the person, or fix it in the phase that owns the file.

## Memory

With `memory` or `hybrid` persistence, also read the state artifact (`.exo/shared/memory-convention.md`). If memory and the files disagree, the files win in `hybrid`; say that they disagree.
