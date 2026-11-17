---
name: prompt-code-sync
description: >-
  Keeps the REASONS canvas (canvas.md) and the code of an SDD change in sync
  during apply, so the code never drifts from its approved contract. Before
  each task it reads the Operations and Safeguards the task implements and
  holds the code to them. When something has to change it classifies it: a
  logic correction (the behavior changes: a rule was wrong, a case was
  missing) changes the canvas first and sends it back to the person's
  approval before any code; a refactor (same behavior) changes the code
  first and then Structure and Operations; a conflict it cannot settle stops
  the task with needs-input. Use it in every apply of a change that has
  canvas.md, and whenever the code and the canvas disagree. Triggers: "the
  code and the canvas drifted", "the canvas is wrong", "update the canvas",
  "logic correction", "which canvas operations does this task implement",
  "keep the canvas in sync with the code".
metadata:
  exo-pack: sdd
  exo-execution: inline
  exo-permissions: write-specs
---

# prompt-code-sync

## Result

- Each task implemented as the canvas says: its Operations performed, its Safeguards kept, its files inside Structure, and the Norms followed.
- Every divergence between canvas and code settled in the right order (`.exo/shared/spdd-common.md`, section D) and recorded as a decision, or the task stopped with `status: needs-input`.
- When apply ends, the canvas and the code describe the same behavior.

The rules of the overlay are in `.exo/shared/spdd-common.md`. When this skill and that contract disagree, the contract wins.

## When

- **Apply, any tier, when `<change-root>/canvas.md` exists** (`.exo/shared/spdd-common.md`, section C). It loads with skill:sdd-apply, in `sdd-implementer` or inline.
- **Rework:** after a `needs-rework` verdict, or a conformance gap from skill:prompt-spec-review, the same rules apply to each fix.
- **On request,** in any phase, when the person says the code and the canvas disagree.
- Without canvas.md there is nothing to sync: say so and go on with skill:sdd-apply.

## Who changes what

| Runs in | Code and tests | canvas.md and the gate |
|---|---|---|
| `sdd-implementer` | the files the plan names (skill:sdd-apply) | never: return the exact canvas edit in the envelope, and the orchestrator's session applies it |
| inline (no subagents, or the orchestrator's session) | the files the plan names | the canvas edits below, each shown to the person and recorded; the gate only through skill:prompt-spec-review |

A canvas edit always names the section, the item, the old text, the new text and the reason. Its format is in `references/sync-cases.md`.

## Before each task

1. **Find what the task implements.** From the task in tasks.md (Tier 3 and 4) or the Scope item (Tier 1 and 2), take its `S-n` and `TM-n`. The Operations that cite them, the Safeguards that touch its files, and every Norm apply.
2. **Read them in full** and note them for the envelope: `Task 2: Operations 1, 2, 3; Safeguards 1; Norms 1-4`.
3. **Check the task against them before any code:** its files are in Structure, and the Operations can be done in the code as it is. A task that needs something the canvas does not say, or says otherwise, is a divergence: classify it first.
4. **Implement** with skill:sdd-apply, tests first. Each test asserts the observable result of its Operation and, where a test can show it, that the Safeguard holds.
5. **Re-read the task's diff** against the Operations and Safeguards you noted. All performed and kept: tick the box and go to the next task.

## Classify each divergence

| What happened | Kind | Order |
|---|---|---|
| The behavior must change: a rule was wrong, a case was missing, an unhappy path must end differently, a Safeguard must change | logic correction | canvas first, approval again, then code |
| Same observable behavior, different code: names, a split inside Structure's files, steps reordered with the same result | refactor | code first, then Structure, and Operations if steps moved; no new approval |
| The fix changes what spec.md requires (a requirement, a scenario's Then) or what design.md decides | spec or design change | stop with `needs-input`: skill:sdd-spec or skill:sdd-design first, then the canvas follows |
| The code cannot follow the canvas and you cannot tell which side is right | conflict | stop with `needs-input`, both sides described |
| Something neither the canvas nor the plan covers: a nearby bug, a cleanup | follow-up | not a sync: list it as skill:sdd-apply says |

- **The test question:** would a test written from the canvas as it is fail after the change? Yes: logic correction. No: refactor.
- **When unsure,** treat it as a logic correction: a person looks at it.
- Worked examples, including the edge cases, are in `references/sync-cases.md`.

## Logic correction

1. **Write the canvas edit:** section, item, old text, new text and the reason (the `S-n`, the `TM-n`, or the person's words).
2. **Check it stays inside the spec.** If the new behavior contradicts a requirement or a scenario, it is a spec change: stop.
3. **Apply it.** Inline: edit canvas.md, keeping the numbering (append, or mark `(removed)`), and run `exo speclint <change-root>`. In `sdd-implementer`: do not edit; return `status: needs-input` with the edit.
4. **Show the person the change** in the canvas: the section before and after.
5. **Back to approval.** The changed canvas goes back to the person: skill:prompt-spec-review runs again in approval mode, even when the gate was already `APPROVED`. No code changes until the person approves the changed canvas. Without that approval (unattended, or no answer), the gate is `ESCALATED` and the task stops with `needs-input`.
6. **Then the code,** test first, as skill:sdd-apply says.
7. **Record the decision** (see Record).

A request from the person to fix the code is not an approval of the canvas change: show the change and ask the gate's question.

## Refactor

1. **Change the code** inside the task's files. The tests stay green without changing what they assert; a test whose assertion has to change means the behavior changed, so it is a logic correction.
2. **Update the canvas:** Structure, and Operations when steps moved, so it describes the code. Run `exo speclint <change-root>`. In `sdd-implementer`, return the edit in the envelope notes for the orchestrator to apply.
3. No new approval. Record the decision.

## Conflict

Stop the task and change neither side. Return `needs-input` with the canvas item, the code at `path:line`, why they cannot both hold, and the options you see:

```yaml
status: needs-input
phase: apply
change_name: add-volume-discount
artifacts: []
notes: >-
  Canvas conflict in task 1: Operations 1 adds up the quantities of all lines and Entities says
  a quantity is 1 or more, but the existing model accepts credit lines with negative quantities
  (src/billing/invoice.py:30). The canvas cannot hold as written. Options: (a) count only the
  positive lines (logic correction in Operations 1 and Entities); (b) reject an invoice with
  credit lines in close() (logic correction: a new unhappy path). Which one?
next: apply
```

## Never

- Never write code that departs from the canvas "for now", meaning to fix the canvas later.
- Never edit the canvas silently: every edit is shown and recorded.
- Never approve a canvas change yourself, and never renumber an approved canvas.

## Record

Each sync is a decision (`.exo/shared/spdd-common.md`, section D). Inline, record before the envelope (`.exo/shared/capability-attribution.md`):

```bash
exo change record <change> --add capabilities_used '{"name": "prompt-code-sync", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"prompt-code-sync"'
exo change record <change> --add decisions '{"summary": "Canvas: logic correction in Operations 3 (round the discount half-even, not up)", "by": "human"}'
exo change record <change> --add decisions '{"summary": "Canvas: refactor, Structure updated (tier lookup in discounts._tier_for)", "by": "agent"}'
```

- In `sdd-implementer`, list the resolution and each sync in the envelope notes; the orchestrator records them.
- In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Return

The apply envelope carries it (`.exo/shared/sdd-phase-common.md`, section D). Add to its notes, per task, what it implemented and each sync:

```text
Canvas: task 1 -> Operations 1, 2, 3, Safeguards 4; task 2 -> Operations 4, 5, 6, Safeguards 1, 2; Norms 1-4 in both.
Syncs: refactor in task 1 (Structure: tier lookup helper in src/billing/discounts.py). Canvas edit for the orchestrator:
Structure, item 1, add "discounts._tier_for(quantity) -> DiscountTier | None picks the tier".
```

## Before you finish

- [ ] Before each task, its Operations, Safeguards and Norms were read and noted.
- [ ] Every divergence classified; a logic correction changed the canvas first and went back to approval before any code.
- [ ] A refactor kept every test assertion and updated Structure (and Operations when steps moved).
- [ ] A spec or design change, or a conflict, stopped the task with `needs-input`; neither side changed silently.
- [ ] In `sdd-implementer`, no edit to canvas.md or the gate: the edits are in the envelope.
- [ ] Each sync recorded as a decision; canvas and code agree at the end.
