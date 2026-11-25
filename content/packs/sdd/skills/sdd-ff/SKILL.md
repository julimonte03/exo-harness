---
name: sdd-ff
description: >-
  Fast-forwards the planning of an SDD change: runs the planning phases its tier
  requires (propose, spec, design, tasks) one after the other and stops before
  apply, so the person reviews the whole plan at once. Use when the person types
  /sdd-ff, or asks to draft the whole plan, all the specs, or everything up to the
  code. Triggers: "fast-forward", "plan it all", "draft every spec", "/sdd-ff".
metadata:
  exo-pack: sdd
  exo-execution: inline
  exo-phase: orchestrate
  exo-permissions: write-specs
---

# sdd-ff

## Result

Every planning artifact the tier requires is in the change root (`proposal.md`, `spec.md`, `test-spec.md`, `design.md`, `tasks.md`, as the tier says), `exo speclint <change-root>` passes, and no code was written. The person reviews the plan as a whole before apply.

## Steps

1. **Which change.** Same as skill:sdd-continue: the named one, the only active one, or ask. Without a change, start it with skill:sdd-new first.
2. **Load the orchestrator.** Read skill:sdd-orchestrator in full and follow `.exo/shared/sdd-phase-common.md`.
3. **Plan the phases.** From `exo change status <change> --json` and the tier (`.exo/shared/phase-skill-map.md`, Phases per tier), list the planning phases still missing, in order:
   - Tier 1: nothing more after `sdd-new` (the proposal, and the delta if behavior changes);
   - Tier 2: spec, with its `test-spec.md`;
   - with the SPDD overlay in Tier 1 and 2, then the canvas and its approval (skill:sdd-orchestrator, SPDD overlay); the person's approval is never skipped;
   - Tier 3: explore when the area is unknown, then propose, spec, design and tasks, with `test-spec.md`.
4. **Run them in a row**, through the orchestrator's loop, without the gate between phases. Still stop at once on `needs-input`, `blocked` or a fitness signal that changes the tier: a change of tier changes the plan.
5. **Check.** `exo speclint <change-root>`; fix what it reports in the phase that owns the file.
6. **Stop before apply.** Show a short summary of each artifact and ask "Adjust anything or continue?". Apply starts only when the person says so.

End with one envelope per phase you ran, the last one with `next: apply`.
