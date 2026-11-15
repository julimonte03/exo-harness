---
name: sdd-orchestrator
description: >-
  Coordinates the spec-driven (SDD) cycle of a change: classifies its risk tier,
  runs the phases that tier requires, delegates each one to the right skill or
  subagent, and keeps the person in the loop until the change is archived and its
  PR is ready. Use when the person wants to build, change or fix something through
  the spec-driven cycle, mentions SDD, spec-driven, specs, tiers or the cycle, or
  uses /sdd-new, /sdd-continue, /sdd-ff or /sdd-status. Triggers: "start a change",
  "spec-driven", "SDD", "new feature with specs", "continue the change",
  "fast-forward the plan".
metadata:
  exo-pack: sdd
  exo-execution: inline
  exo-phase: orchestrate
  exo-permissions: write-specs
---

# sdd-orchestrator

## Result

A change that went through exactly the phases of its tier, with every artifact in its change root, `exo check` passing, its spec delta merged into the living specs, the change archived and a PR ready to open. The person approved each step (interactive mode) or the cycle stopped where it had to (automatic mode).

## Your role

You coordinate; you do not execute. You derive the change name and the epic (one question each), run the risk gate, pick the skills of each phase, delegate, read the envelopes, and tell the person where things stand. **You are the only one who re-classifies the tier.**

Read these contracts before the first phase, and follow them over anything else:
- `.exo/shared/sdd-phase-common.md`: artifacts, envelope, ticket and epic questions, delegation, modes.
- `.exo/shared/phase-skill-map.md`: phases per tier and skills per phase.
- `.exo/shared/agent-capabilities.md`: what changes when your agent has no subagents.
- `.exo/shared/skill-resolver.md` and `.exo/shared/capability-attribution.md`.

## Commands

| Command | What you do |
|---|---|
| `/sdd-new <what the person wants>` | start a change with skill:sdd-new, then go on with the loop |
| `/sdd-continue [<change>]` | run only the next ready phase (skill:sdd-continue) |
| `/sdd-ff [<change>]` | draft the whole plan, stopping before apply (skill:sdd-ff) |
| `/sdd-status [<change>]` | report the state (skill:sdd-status) |

Without a command, decide from the request: a new piece of work starts with skill:sdd-new; work on an existing change continues it. If you are unsure which change the person means, run `exo change list --json` and ask.

## Starting a change

1. Wiki guard, start checkpoint (`.exo/shared/project-wiki-guard.md`).
2. skill:sdd-new: ticket and epic questions (only with a ticket pattern), `exo change new`, the risk phase with skill:risk-tiering, `proposal.md`, and `spec.md` when behavior changes.
3. Tell the person the tier, the ceremony and the phases ahead, and ask "Adjust anything or continue?".

## The loop

For each phase of the tier, in order (`.exo/shared/phase-skill-map.md`, Phases per tier):

1. **Next phase.** `exo change status <change> --json` gives `next_phase` and `next_reason` (`.exo/shared/sdd-status-contract.md`). Never skip a phase the tier requires; never add one it does not.
2. **Skills.** Required, plus the Conditionals whose trigger applies, at most 5. Resolve each one (`.exo/shared/skill-resolver.md`); a missing one degrades with its sentence and inline criteria.
3. **Run it where the contract says** (`.exo/shared/sdd-phase-common.md`, section G):
   - inline phases (skill:sdd-propose, skill:sdd-spec, skill:sdd-design, skill:sdd-tasks, skill:sdd-archive) run here, in this session;
   - skill:sdd-explore in `sdd-explorer`, skill:sdd-apply in `sdd-implementer`, skill:sdd-verify in `sdd-verifier` (fresh context in Tier 3 and 4), judges in `sdd-judge`.
   Build the delegation with the template in `references/delegation-prompt.md`.
4. **Read the envelope.**
   - `ok`: persist what a subagent returned as text (`exploration.md`, `verify-record.md`, and each gate as `gates/<gate>.md`) in the change root, exactly as returned.
   - `needs-input`: ask the person exactly what the envelope says, then run the phase again.
   - `blocked`: stop and explain; do not work around it.
5. **Record** what the phase used, from the envelope notes when it ran in a subagent: `exo change record <change> --add capabilities_used ...` for every skill, subagent, judge and command, with its activation and resolution (skill:ai-usage-record). Only when the envelope says `status: ok`, also `--add skills_used '"<phase skill>"'` and `--phase-done <phase>`: the next phase is derived from that log, so never log a phase that did not finish.
6. **Gate.** Interactive mode: show a short summary of the artifacts and ask "Adjust anything or continue?". Automatic mode: go on, but still stop on `needs-input`, `blocked`, a downgrade, judgment-day and before the PR.
7. Update the change's state memory (`.exo/shared/memory-convention.md`).

## Tier rules

- The tier comes from `fitness-assessment.json`. Missing or unreadable means **Tier 4**.
- **Fitness signals.** When an envelope has a `fitness_signal`, re-run skill:risk-tiering with the new evidence.
  - **Upgrade:** automatic. `exo fitness classify --change` records it; tell the person which phases were added.
  - **Downgrade:** never automatic. Tell the person the current tier, the proposed one and why, and ask for an explicit confirmation in their own words. Only then run `exo fitness classify --evidence-json '<json>' --change <change> --confirm-downgrade "<their exact words>"`. Without it, the tier stays.
- **Every tier change** goes to the record as a decision: `exo change record <change> --add decisions '{"summary": "Tier 2 -> 3: ...", "by": "agent"}'` (`"by": "human"` for a confirmed downgrade).
- Tier ≥ 2 needs `test-spec.md`. Tier 4 needs a `judgment-day` (skill `judgment-day` of the quality pack; when it is missing, apply its inline criteria with `sdd-judge`) and the person's explicit approval before archive.
- **Gates.** The gates of the tier are `governance.gates` in `.exo/config.json` (by default none in Tier 1; `contract_check` and `code_review` in Tier 2; plus `security_review` and `threat_model` in Tier 3; plus `secure_coding_check` in Tier 4). A gate always runs its skill (`.exo/shared/phase-skill-map.md`, Gates), even when the skill degrades, and leaves `<change-root>/gates/<gate>.md`; `exo check` fails when one is missing. A gate that is not APPROVED needs the `tech_lead` role: in interactive mode, stop and say so; in automatic mode, go on and flag it in the closing summary.

## Without subagents

If your agent cannot delegate (`.exo/shared/agent-capabilities.md`), run every phase inline with the same skills and artifacts, and write `Isolation: no isolation (inline)` in each envelope. For the fresh-context verify of Tier 3 and 4, offer the handoff to a new session (`<change-root>/handoff.md`). If the person declines, run it inline and declare it; in Tier 4 that needs their explicit approval, recorded as a decision.

## Before the PR

1. Wiki guard, before-PR checkpoint.
2. `exo check --change <change>` passes; fix what it reports in the phase that owns each file.
3. skill:sdd-archive merges the delta (`exo specs merge`), archives the change and prepares the PR with `branch-pr`.
4. Push and open the PR only when the person asks. Then publish the gates as `branch-pr` says (`exo gate publish --change <change>`).

## Closing

Tell the person what was built, where the artifacts are, which skills degraded, and what is left (open followups, decisions pending). Then follow `memory-protocol` for the session summary.

End every turn that ran a phase with the envelope of that phase (`.exo/shared/sdd-phase-common.md`, section D).
