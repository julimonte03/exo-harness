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

`exo change status <change> --json` returns `next_phase` and `next_reason`, computed with these rules in this order; the first one that applies wins. Report them as they are: do not re-derive them by hand.

1. no readable `fitness-assessment.json` → `risk`;
2. no `proposal.md` → `new`;
3. Tier 3 and 4: the proposal says "The area is unknown" (`sdd-new` writes "The area is unknown: explore before proposing." in Approach) and there is no `exploration.md` → `explore`; `propose` is not in `phases_done` → `propose`;
4. Tier ≥ 2 without `spec.md`, or Tier 2 without `test-spec.md` → `spec`;
5. Tier 3 and 4 without `design.md` → `design`; without `tasks.md` or `test-spec.md` → `tasks`;
6. the Verdict of `verify-record.md` is `needs-rework`: if the last entry of `phases_done` is not `apply` → `apply`, to fix what Issues Found lists; once that apply is logged → `verify` again;
7. Tier 3 and 4 with unchecked boxes in `tasks.md`, or Tier 1 and 2 without `apply` in `phases_done` → `apply`;
8. no `verify-record.md`, a Verdict that is not valid, or `blocked` → `verify`;
9. Tier 4 without `{"name": "judgment-day", "result": "approved"}` in `judges_invoked` → `judgment`;
10. otherwise → `archive`. An archived change gives `none`.

### The phase log

`phases_done` in the AI Usage Record is the ordered log of the phases that finished. When a phase returns `status: ok`, log it with `exo change record <change> --phase-done <phase>`: the phase itself when it ran inline, the orchestrator when it ran in a subagent. Never log a phase that ended with `needs-input` or `blocked`. Logging the same phase twice in a row changes nothing.

## Inconsistencies

Report them, do not resolve them by guessing:

- an artifact of a later phase without the earlier one the tier requires (for example `design.md` without `spec.md` in Tier 3);
- a `change_name` in `ai-usage-record.json` that does not match the folder;
- a Verdict `ready` with open followups (`exo change followups <change>`: neither fixed nor dismissed) or with findings in Issues Found that the person did not decide;
- an unreadable JSON file (it shows up in `warnings`).

Say which file and what is wrong, and ask the person, or fix it in the phase that owns the file.

## Memory

With `hybrid` persistence, also read the state artifact (`.exo/shared/memory-convention.md`); if memory and the files disagree, the files win: say that they disagree. With `memory` persistence there are no files: take the phase and the artifacts from the state artifact and the artifacts saved in memory.
