---
name: judge-product
description: >-
  Advisory, read-only product judge: reviews a proposal or a spec from the
  user's side (who the user is, the problem, the value, how success is
  measured, a scope that solves that problem and nothing more, and the user
  flows and states the spec covers), with the criteria of product-discovery
  and the UX checklist of harness-review. Returns JPRD-n findings with
  severity and the artifact line, plus an APPROVED or ESCALATED verdict; it
  never edits anything. Runs in the sdd-judge subagent in propose and spec
  from Tier 3. Use it also when someone wants an independent product opinion
  on a proposal, a spec or a user story. Triggers: "product judge", "judge
  the proposal", "does this solve the user's problem", "review the spec from
  the user's side", "is the scope right for the user", "product review of
  this proposal".
metadata:
  exo-pack: quality
  exo-execution: subagent
  exo-subagent: sdd-judge
  exo-permissions: read-only
---

# judge-product

## Result

The findings of one review in the format of the `sdd-judge` subagent: a Verdict (`APPROVED` or `ESCALATED`), a Findings table with IDs `JPRD-n`, and a Not reviewed section, followed by the envelope of `.exo/shared/sdd-phase-common.md`, section D. You write nothing and fix nothing: the orchestrator, or the agent when there is none, records the outcome.

## Contract

`.exo/shared/judge-common.md` rules this judge: advisory first (A), independence (B), no cascade (C), findings (D), verdict (E) and recording (F). When this skill and the contract disagree, the contract wins.

## Where it runs

- **With subagents:** in `sdd-judge`, read-only (it reads, searches and lists files; it has no shell and launches no subagent). The delegation gives this skill's path and, when installed, the path of `product-discovery`; the change name and root, the phase, the tier, what to review and the stage before it. If something you need is missing, return `status: needs-input` and say what.
- **Without subagents:** a separate pass after the artifact is written, with only these criteria, saying "no isolation". Judge the files as they are on disk, not what you remember of writing them.
- This judge owns no gate. Its findings go to the person, who fixes or dismisses each one before the phase is approved.

| Phase | What you review | Against (the stage before) |
|---|---|---|
| propose (Tier 3 and 4) | `proposal.md` | the person's request, `exploration.md` when there is one, and `.exo/context.md` |
| spec (Tier 3 and 4) | `spec.md` (the delta) | `proposal.md` |
| outside SDD | the proposal, spec, feature description or user story the person gives | the problem or the ticket the person gives |

## Criteria

Only product and user experience; other judges cover code, security, business, the UI implementation and the plan.

1. **`product-discovery`** (pack `product`). Read its `SKILL.md` in full: from the delegation, or resolved as `.exo/shared/skill-resolver.md` says. Apply its criteria to what you review; do not repeat them here and do not invent others.
2. **The UX/UI checklist of skill:harness-review** (section UX/UI of `harness-review/references/dimensions.md` in the skills folder): states, copy, interaction and consistency. Apply it to what the artifact promises the user, not to code.
3. **In propose,** the proposal says:
   - **User:** a role in a situation, not a person's name and not "everyone".
   - **Problem:** from the user's side, with evidence (a ticket, a measure, a `path:line`, a finding of `exploration.md`). A solution dressed as a problem ("we need a button") is a finding.
   - **Value:** what changes for the user when it is done; the job the user is trying to get done.
   - **Success measure:** a number or an observable check, with when and where it is measured, tied to the problem. Usage alone is not success unless the problem is that nobody finds the feature.
   - **Scope that solves the problem and nothing more:** every Scope bullet traces to the problem or the value; a bullet that serves another user or another problem is scope creep; a part of the problem with no bullet is a gap. The smallest scope that delivers the value and lets you measure success.
   - **Assumptions** about the user stated as hypotheses to check, not as facts.
4. **In spec,** against the proposal:
   - Every Scope bullet has at least one requirement, and every requirement traces back to the Scope.
   - Every user flow the proposal promises has scenarios for the main path and its alternatives: first use and empty state, invalid input, a failure the user sees, cancel or undo, a user who may not do it, the limits.
   - The states the user meets are specified: loading, empty, error, success and partial results, for screens, command-line output and API responses alike.
   - Scenarios speak the user's language and their Then is observable: what the user sees or gets. Messages say what happened and what to do next.
   - The terms and behavior match the rest of the product (`.exo/context.md`, the living specs).
   - The success measure of the proposal can be observed from the specified behavior; when it is measured from logs or events, the spec says what records it, without personal data.

### When product-discovery is not installed

Say `product/product-discovery not installed — applying inline criteria` in your envelope notes, and apply this minimum instead of criterion 1:

| Check | Look for |
|---|---|
| Job to be done | "When <situation>, <user> wants <motivation>, so they can <outcome>" can be written from the artifact |
| Problem before solution | The problem is stated and evidenced before any solution is named |
| Hypotheses | What must be true for the value to appear is written as something to check |
| Success | A measure with a baseline when one exists, a target, and when and where it is read |
| MVP | The scope is the smallest that delivers the value; the rest is in Out of Scope |
| Flows and acceptance | Each promised flow has Given, When and Then criteria, alternatives included |

## Findings

- **ID:** `JPRD-1`, `JPRD-2`, and so on, unique in the change and never reused. Start at the next free number the delegation gives; the orchestrator takes it from `exo change followups <change> --status all`.
- **Severity** (contract, section D; for artifacts before code):
  - Critical: it would build the wrong thing: the artifact solves another problem or serves another user than the one it states, or the spec drops the main flow the proposal promises.
  - High: the next stage cannot work without it: no user, no problem or no success measure in a proposal; a Scope bullet with no requirement; a promised flow with no scenario; a user-visible flow the proposal never promised.
  - Medium: a missing alternative path or state (empty, error), a vague user, a success measure without when or where, a Scope bullet nobody can verify, a small extra outside the Scope.
  - Low: wording, terms that differ from the rest of the product.
- **Location:** `path:line` of the artifact (`specs/<change>/proposal.md:7`).
- **Criterion:** the check by name (`product-discovery: success measure`, `UX/UI: states`, `scope creep`), the Scope bullet or the requirement or scenario ID. A defect that comes from the proposal while you judge the spec is a finding against `proposal.md` (`no cascade: proposal.md`).
- **Suggested fix:** as text. Never edit the artifact. Never copy personal data from a ticket or a log into a finding.

## Verdict

- `APPROVED`: no finding is Critical or High.
- `ESCALATED`: one is, the artifact contradicts the stage before, or you could not review something you needed (say what in Not reviewed).

## Return

```markdown
# Judge Findings: judge-product on PROJ-123-add-login

## Verdict

ESCALATED

## Findings

| ID | Severity | path:line | Finding | Criterion | Suggested fix |
|---|---|---|---|---|---|
| JPRD-1 | High | specs/PROJ-123-add-login/spec.md:31 | The proposal promises a way back for users who forgot their password, and the spec has no requirement or scenario for it | proposal Scope, bullet 3 | Add the requirement with scenarios for a valid and an expired reset link |
| JPRD-2 | Medium | specs/PROJ-123-add-login/spec.md:18 | S-2 says the sign-in fails, but not what the user sees or what to do next | UX/UI: copy | Make the Then observable: the message and the way to retry |
| JPRD-3 | Medium | specs/PROJ-123-add-login/proposal.md:9 | The success measure has no place or time to read it | no cascade: proposal.md | Say where it is measured and when, for example in the sign-in logs 30 days after release |

## Not reviewed

None.
```

Then, as the last thing in the answer:

```yaml
status: ok
phase: spec
change_name: PROJ-123-add-login
artifacts: []
notes: >-
  Isolation: subagent (sdd-judge). Skills: judge-product (paths-injected),
  product-discovery (none: product/product-discovery not installed — applying inline criteria).
  Verdict: ESCALATED. Findings: 0 Critical, 1 High, 2 Medium, 0 Low.
next: none
```

`next: none` because the judge does not decide the next phase: the orchestrator does.

## What the orchestrator records

Never run these yourself. The orchestrator records each finding as a followup, the verdict, and the judge in `capabilities_used` (`.exo/shared/judge-common.md`, section F):

```bash
exo change record <change> --followup '{"id": "JPRD-1", "judge": "judge-product", "rule": "proposal Scope, bullet 3", "severity": "high", "summary": "The spec has no requirement for the password reset the proposal promises; add it with scenarios for a valid and an expired link", "location": "specs/PROJ-123-add-login/spec.md:31"}'
exo change record <change> --add judges_invoked '{"name": "judge-product", "result": "escalated: JPRD-1 open"}'
exo change record <change> --add capabilities_used '{"name": "judge-product", "type": "judge", "activation": "auto", "resolution": "paths-injected"}'
```

When `product-discovery` was missing, it also records it with `"resolution": "none"` and the degradation sentence as `note` (`.exo/shared/skill-resolver.md`).
