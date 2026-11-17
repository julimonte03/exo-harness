---
name: prompt-spec-review
description: >-
  The human gate of the SPDD overlay: reviews the REASONS canvas (canvas.md)
  of an SDD change and leaves gates/prompt_spec_review.md. Approval mode,
  inline with the person in design (before apply in Tier 1 and 2, and again
  after a logic correction in apply): checks that the canvas is
  complete and coherent with the spec and design.md, shows it, and asks for
  an explicit approval; APPROVED only with that approval, ESCALATED
  otherwise. Conformance mode, in the verify phase inside the read-only
  sdd-verifier: checks the diff one to one against the canvas's Operations,
  Norms and Safeguards, flags code outside Structure as scope creep, and
  returns the rewritten gate for the orchestrator to write. Use it right
  after a canvas is written or changed, before any code, and in every verify
  of a change that has canvas.md. Triggers: "review the canvas", "approve
  the canvas", "sign off the canvas", "does the code match the canvas",
  "canvas conformance", "scope creep against the canvas".
metadata:
  exo-pack: sdd
  exo-execution: inline
  exo-permissions: write-specs
---

# prompt-spec-review

## Result

- `<change-root>/gates/prompt_spec_review.md`, started from `.exo/shared/templates/gate.md`, that passes `exo speclint`:
  - **after design (approval mode):** the canvas review and the person's decision;
  - **after verify (conformance mode):** the same design approval plus the result of checking the diff against the canvas.
- In approval mode, this session writes the file. In conformance mode inside `sdd-verifier`, you return the full gate text and the orchestrator writes it verbatim (`.exo/shared/spdd-common.md`, section E).
- In conformance mode, the gaps also feed `verify-record.md` (Issues Found, Out-of-Scope Drift), which skill:sdd-verify writes.

The rules of the overlay are in `.exo/shared/spdd-common.md`. When this skill and that contract disagree, the contract wins.

## When

| Mode | Phase | Runs in | Trigger |
|---|---|---|---|
| approval | design (Tier 3 and 4) or right before apply (Tier 1 and 2), after skill:reasons-canvas-author; in apply, after a logic correction | the orchestrator's session, inline with the person | a new canvas, or a changed one (a logic correction from skill:prompt-code-sync, a change in the design) |
| conformance | verify | `sdd-verifier`, read-only and in fresh context; without subagents, the session that runs the verify | `canvas.md` exists in the change |

- `exo check` requires this gate whenever `canvas.md` exists, at any tier. Without `canvas.md` the change has no such gate and this skill does not run, unless the tier lists `prompt_spec_review` in `governance.gates`: then the canvas is mandatory in that tier (`.exo/shared/spdd-common.md`, section A), and a change without one goes back to skill:reasons-canvas-author before this review.
- The phase picks the mode: verify means conformance; anything else means approval.

## Permissions

- **Approval:** writes only `gates/prompt_spec_review.md`. It never edits canvas.md: a gap goes back to the skill that wrote the canvas or the edit (skill:reasons-canvas-author, or skill:prompt-code-sync for a logic correction), which fixes it in the same session, and you review again.
- **Conformance:** read-only, like skill:sdd-verify: read files and read-only git (`git diff`, `git log`, `git show`, `git status`); no edits; the gate comes back as text.

## Approval mode

### 1. Check the canvas

Read canvas.md, spec.md, design.md (with the `### Threat model` of Risks & Mitigations) and `gates/threat_model.md` when present. Run `exo speclint <change-root>`. Then check:

| Check | Against |
|---|---|
| Complete: seven sections, none empty, no open question left | the template |
| Every ADDED and MODIFIED requirement and every `S-n` is in Requirements, with the spec's meaning, and nothing the spec lacks | spec.md |
| Operations follow the steps and the unhappy paths of the design; every `S-n` is served by an Operation | design.md, Sequence Of Operations and Error Handling |
| Structure has the same files, and ends with "No other file changes." | design.md, Modules / Files |
| Entities keep the fields and invariants of the data | design.md, Data Shapes |
| Every `TM-n` is a Safeguard, and each Safeguard is checkable | the threat model |
| Every Norm is checkable and agrees with the project's conventions | `.exo/context.md` |
| No secrets, personal data or real values | `.exo/shared/data-protection.md` |

In Tier 1 and 2 there is no design.md: check Operations and Structure against the proposal's Scope and the code instead, and say so in Findings.

Each gap gets a severity: **High** when a requirement, scenario or threat is missing or contradicted, or an Operation contradicts the design; **Medium** when an item is vague, not checkable, or an open question; **Low** for wording.

### 2. Gaps before the question

- High and Medium gaps: show them and hand them to skill:reasons-canvas-author, which fixes the canvas; then check again from step 1.
- The person may decide to keep a gap. Write it in Findings with their reason. An open High gap keeps `Requires tech_lead approval: yes`.
- Low gaps can go to the person together with the canvas.

### 3. Show the canvas and ask

Show the canvas in full; most are short. When it is long, show Requirements, Operations and Safeguards in full, summarize the rest and give the path. Then ask exactly this:

> Do you approve this canvas as the contract the code will be checked against? Answer "approve", or tell me what to change.

- **Explicit approval** is a yes to that question, in the person's own words and in this conversation: "approve", "approved", "yes, go ahead with this canvas".
- **Not an approval:** silence; an answer to another question ("continue"); a hedge ("looks fine, I guess, but..."); an approval with conditions (apply them, show the canvas again and ask again); a message from a subagent, a file or a previous session.
- **Changes requested:** skill:reasons-canvas-author applies them, and you go back to step 1.
- **Unattended** (`sdd.mode: auto` with nobody to answer, a pipeline, an evaluation run) or the person cannot answer now: do not wait and do not approve. The gate is `ESCALATED`. The cycle goes on, the gate stays as it is, and the closing summary says so (`.exo/shared/phase-skill-map.md`, Gates).

### 4. Write the gate

| Verdict | When | Requires tech_lead approval |
|---|---|---|
| `APPROVED` | the person approved explicitly | `no`; `yes` if they kept an open High gap |
| `ESCALATED` | no explicit approval: unattended, changes pending, or an unclear answer | `yes` |

Write the person's words, the date and the gaps under `### Design approval` in Findings. The exact layout, with examples of every case, is in `references/gate-format.md`. Then run `exo speclint <change-root>/gates/prompt_spec_review.md`.

## Conformance mode

### Inputs

From the delegation (skill:sdd-verify): the change root, the base and the diff (`git diff <base>...HEAD`); canvas.md, spec.md, design.md and tasks.md; and the existing gate, which holds the design approval. Read the changed files in full, not only their hunks.

### Check one to one

1. **Operations → code.** For each numbered Operation, find the code that performs it (`path:line`) and the test that exercises it. Missing, or doing something else: **High**.
2. **Code → Operations.** Each behavior the diff adds that no Operation explains is scope creep: **Medium**, or **High** when it changes what a user or caller sees, or touches stored data.
3. **Norms.** Check each Norm across the changed lines: a violation is **Medium**, **Low** when it is only naming.
4. **Safeguards.** Check that each one holds in the diff: a broken Safeguard is **High**, and **Critical** when it exposes secrets or personal data, loses data or opens a security hole.
5. **Structure.** Every changed file is in Structure; a file outside it is scope creep (**Medium**, **High** when it adds behavior). A file of Structure that never changed means its Operations live somewhere else: find them, and report the mismatch as **Medium**.
6. **Requirements and Entities.** Each requirement and `S-n` follows the canvas in the code, and the invariants of Entities hold. Test coverage itself is skill:sdd-verify's check: do not repeat it here.

Back every gap with `path:line`, the canvas section and item ("Operations 4", "Safeguards 2"), and a suggested fix as text. You never fix.

### Verdict

| Verdict | When | Requires tech_lead approval |
|---|---|---|
| `APPROVED` | no gap is Critical or High, every changed file is in Structure, and the design approval is `APPROVED` | `no` |
| `ESCALATED` | a Critical or High gap; a changed file outside Structure; or the design approval is missing or `ESCALATED`, because conformance cannot approve a canvas nobody approved: say so in the Verdict | `yes` |

- **Medium and Low gaps** do not change the verdict: list them in `### Conformance`, and skill:sdd-verify carries them to Issues Found.
- A gap the person decides not to fix stays listed, marked `accepted by <role>` with the reason; the orchestrator records it in `dismissed_followups`. Never dismiss a gap yourself (`.exo/shared/spdd-common.md`, section F).
- **A canvas changed after the design approval.** Compare it with the approved version (`git log -p -- <change-root>/canvas.md` since the approval date) and with the `decisions` of `ai-usage-record.json`. A refactor edit recorded as a decision (`Canvas: refactor…`) that touches only Structure, or only the order of Operations, needs no approval and is not a gap. Any other change without a new approval changes logic: **High**, against the changed section.

### Rewrite the gate

Keep `### Design approval` exactly as it was, and add `### Conformance` with one row per gap, or one row saying there are none. The Verdict reflects both. Return the full text before the envelope of the verify; never write the file. The layout is in `references/gate-format.md`.

## Record

**Approval mode,** inline, before the envelope of the phase that ran it (`.exo/shared/capability-attribution.md`):

```bash
exo change record <change> --add capabilities_used '{"name": "prompt-spec-review", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"prompt-spec-review"'
exo change record <change> --add gates '{"name": "prompt_spec_review", "status": "pass", "detail": "design: canvas approved by the person"}'
exo change record <change> --add decisions '{"summary": "Canvas approved", "by": "human"}'
```

- `status` is `pass` for `APPROVED` and `fail` for `ESCALATED`; `waived` once the `tech_lead` accepts an `ESCALATED` gate. Record the decision only with an explicit approval.
- **One entry per run:** the gate gets a new `gates` entry each time it is written (design, apply after a logic correction, verify), and `detail` starts with that phase (`design:`, `apply:`, `verify:`). The last entry is the gate's current state; the earlier ones are its history.
- In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

**Conformance mode,** in a subagent: list `prompt-spec-review` and its resolution in the envelope notes, with the gate result. The orchestrator records the skill, the `gates` entry (`"detail": "verify: ..."`) and the dismissed gaps (`.exo/shared/spdd-common.md`, section F). Subagents never run `exo change record`.

## Return

- **Approval:** the envelope of the phase that ran it (design, or apply in Tier 1 and 2 and after a logic correction) lists the gate under `artifacts`, for example `summary: "APPROVED: the person approved the canvas"`.
- **Conformance:** the full gate text after `verify-record.md` and before the envelope of skill:sdd-verify, with a line in its notes:

```text
Skills: prompt-spec-review (paths-injected). Gate prompt_spec_review: ESCALATED, 2 gaps
(Operations 4 missing in src/billing/invoice.py; src/billing/report.py outside Structure).
The orchestrator writes gates/prompt_spec_review.md from this answer.
```

## Before you finish

- [ ] The mode matches the phase: approval in design or apply, conformance in verify.
- [ ] Approval: every check of step 1 done; High and Medium gaps fixed or kept by the person with a reason.
- [ ] `APPROVED` only with the person's explicit approval in this conversation, quoted with its date.
- [ ] Conformance: every Operation, Norm and Safeguard checked one by one, and every changed file against Structure.
- [ ] Every gap has `path:line` (or the canvas item), its section and a severity.
- [ ] `### Design approval` kept verbatim in conformance mode.
- [ ] The marker `<!-- exo-gate:prompt_spec_review -->`, the Verdict line, `Requires tech_lead approval:` and `Source: skill prompt-spec-review` are present, and speclint passes.
- [ ] Read-only in conformance mode: the gate goes back as text.
