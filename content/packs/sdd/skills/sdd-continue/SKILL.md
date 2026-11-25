---
name: sdd-continue
description: >-
  Runs only the next ready phase of an SDD change and stops: no more, no less.
  Use when the person types /sdd-continue, or asks to continue, resume or go on
  with a change, or to do "the next step" of a spec-driven change. Triggers:
  "continue the change", "next phase", "resume the spec", "/sdd-continue".
metadata:
  exo-pack: sdd
  exo-execution: inline
  exo-phase: orchestrate
  exo-permissions: write-specs
---

# sdd-continue

## Result

The next phase the change's tier requires has run, its artifact is in the change root, and you stopped there: the person sees the summary and decides what follows.

## Steps

1. **Which change.** If the person named it, use that one. Otherwise run `exo change list --no-archived --json`: one active change, use it; several, ask which; none, offer `/sdd-new`.
2. **Load the orchestrator.** Read skill:sdd-orchestrator in full: you act as the orchestrator for one phase, with its tier rules and delegation. Follow `.exo/shared/sdd-phase-common.md`.
3. **Next phase.** `exo change status <change> --json`, then the rules of `.exo/shared/sdd-status-contract.md`, Next phase. If the state is inconsistent, report it and stop: do not guess.
4. **The anchor.** If the change root has `context-anchor.md`, read it first (Now and Open questions), as skill:context-anchoring says in Resume from the anchor. A next step or a decision that the engine's state or the artifacts contradict goes to the person before the phase runs.
5. **Run that phase only**, through the orchestrator's loop (skills, where it runs, envelope, record, state memory, and the anchor when there is one).
6. **Stop.** Show what the phase produced and the phase that comes next, and ask "Adjust anything or continue?". Do not start the following phase, even in automatic mode: `/sdd-continue` means one phase.

If the next phase is `archive`, run it only after the checks it requires (skill:sdd-archive). If it is `verify` in Tier 3 and your agent has no subagents, offer the fresh-context handoff (`.exo/shared/agent-capabilities.md`).

End with the envelope of the phase you ran.
