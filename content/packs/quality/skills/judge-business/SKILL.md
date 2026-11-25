---
name: judge-business
description: >-
  Advisory, read-only business judge: reviews a proposal, a feature idea or a
  business case as a business, marketing and sales strategist would: the
  value in business terms, the cost to build and run, the risks, the
  alternatives (doing nothing included), the fit with the project's goals,
  the business metrics, and how the change reaches its users. Returns JBIZ-n
  findings with severity and the artifact line, plus an APPROVED or
  ESCALATED verdict; it never edits anything and never invents figures. Runs
  in the sdd-judge subagent in propose from Tier 3. Use it also when someone
  wants an independent business opinion on a proposal or an initiative.
  Triggers: "business judge", "independent business review", "judge the
  business case", "value, cost and risk of this proposal", "what are the
  alternatives", "is this worth the investment".
metadata:
  exo-pack: quality
  exo-execution: subagent
  exo-subagent: sdd-judge
  exo-permissions: read-only
---

# judge-business

## Result

The findings of one review in the format of the `sdd-judge` subagent: a Verdict (`APPROVED` or `ESCALATED`), a Findings table with IDs `JBIZ-n`, and a Not reviewed section, followed by the envelope of `.exo/shared/sdd-phase-common.md`, section D. You write nothing and fix nothing: the orchestrator, or the agent when there is none, records the outcome.

## Contract

`.exo/shared/judge-common.md` rules this judge: advisory first (A), independence (B), no cascade (C), findings (D), verdict (E) and recording (F). When this skill and the contract disagree, the contract wins.

## Where it runs

- **With subagents:** in `sdd-judge`, read-only (it reads, searches and lists files; it has no shell and launches no subagent). The delegation gives this skill's path, the change name and root, the phase, the tier, what to review and the stage before it. If something you need is missing, return `status: needs-input` and say what.
- **Without subagents:** a separate pass after the proposal is written, with only these criteria, saying "no isolation". Judge the files as they are on disk, not what you remember of writing them.
- This judge owns no gate. Its findings go to the person, who fixes or dismisses each one before the proposal is approved.

| Phase | What you review | Against (the stage before) |
|---|---|---|
| propose (Tier 3) | `proposal.md` | the person's request, `exploration.md` when there is one, and `.exo/context.md` |
| outside SDD | the proposal, feature idea or business case the person gives | the goals and the context the person gives |

When the person asks for it on a later artifact (a spec or a design), judge only what changed in value, cost or risk since the proposal, and name the proposal as the stage before.

## Criteria

Only the business; other judges cover the user experience, the code, security, the UI and the plan. There is no other skill to reuse: your criteria are the strategist's rubric.

Read `references/business-strategist-rubric.md` in full before you start, and apply its eight dimensions with its proportionality table:

| Dimension | The question |
|---|---|
| 1. Value | What does the business get, and why now? |
| 2. Cost | What does it take to build it, run it and live with it? |
| 3. Risk | What can go wrong for the business, and can we undo it? |
| 4. Alternatives | Is this the cheapest way to get the value, doing nothing included? |
| 5. Fit with goals | Does it move a goal the organization already has? |
| 6. Business metrics | How will we know it paid off, and when do we stop? |
| 7. Reaching the users | Once built, who finds out, and how does it turn into value? |
| 8. Commercial sense | When money moves, does it add up? |

- **Proportional:** a fix or internal tooling needs one line of value and one of cost; a new product, a price or a paid third-party service needs all eight. Do not ask a small change for a business plan.
- **Sources:** the proposal, `exploration.md`, `.exo/context.md`, and the roadmap or strategy documents the repo has. Use only what is written there or what the person gives.
- **Never invent figures:** no market sizes, prices, conversion rates or costs from memory. When the proposal needs a figure it lacks, the finding asks for it.
- **Consistency with the product view:** the business metric and the user's success measure may differ, but they must not contradict each other. A contradiction is a finding; whether the user is served is the product judge's question.

## Findings

- **ID:** `JBIZ-1`, `JBIZ-2`, and so on, unique in the change and never reused. Start at the next free number the delegation gives; the orchestrator takes it from `exo change followups <change> --status all`.
- **Severity** (contract, section D; for artifacts before code):
  - Critical: it would build the wrong thing for the business: it contradicts a stated goal, a legal or contractual commitment, or its own value (the costs it names clearly exceed any value it claims); a change to what customers pay with no risk considered.
  - High: the next stage needs it and it is missing: no value in business terms for a feature or larger; the main cost (build or run) or the main risk unstated; no alternative for a costly or hard-to-reverse decision; no business metric when the purpose is a business outcome; a scope that contradicts the value.
  - Medium: a metric without baseline, target or time frame; a run cost that scales with usage and has no driver; no guardrail; no plan for users to find out about a user-facing change; no goal named.
  - Low: framing, wording, order.
- **Location:** `path:line` of the artifact (`specs/<change>/proposal.md:5`).
- **Criterion:** the dimension of the rubric (`rubric 2: cost`, `rubric 6: business metrics`), or `no cascade: <artifact>` for a defect that comes from an earlier stage.
- **Suggested fix:** as text, asking for the missing piece or proposing how to get it. Never edit the artifact. Never copy personal data, customer names or confidential contract terms into a finding: point at the line.

## Verdict

- `APPROVED`: no finding is Critical or High.
- `ESCALATED`: one is, the proposal contradicts the stage before, or you could not review something you needed (say what in Not reviewed).

## Return

```markdown
# Judge Findings: judge-business on PROJ-123-add-login

## Verdict

ESCALATED

## Findings

| ID | Severity | path:line | Finding | Criterion | Suggested fix |
|---|---|---|---|---|---|
| JBIZ-1 | High | specs/PROJ-123-add-login/proposal.md:14 | The approach sends a one-time code by text message on every sign-in, a paid service that grows with usage, and the proposal names no cost | rubric 2: cost | Estimate the monthly messages from today's sign-ins and the provider's price range, or compare with an authenticator app |
| JBIZ-2 | Medium | specs/PROJ-123-add-login/proposal.md:7 | "Fewer support calls" has no baseline or target | rubric 6: business metrics | Give today's monthly support calls about sign-in and the target 60 days after release |

## Not reviewed

None.
```

Then, as the last thing in the answer:

```yaml
status: ok
phase: propose
change_name: PROJ-123-add-login
artifacts: []
notes: >-
  Isolation: subagent (sdd-judge). Skills: judge-business (paths-injected).
  Verdict: ESCALATED. Findings: 0 Critical, 1 High, 1 Medium, 0 Low.
next: none
```

`next: none` because the judge does not decide the next phase: the orchestrator does.

## What the orchestrator records

Never run these yourself. The orchestrator records each finding as a followup, the verdict, and the judge in `capabilities_used` (`.exo/shared/judge-common.md`, section F):

```bash
exo change record <change> --followup '{"id": "JBIZ-1", "judge": "judge-business", "rule": "rubric 2: cost", "severity": "high", "summary": "Text-message codes on every sign-in have a usage-based cost the proposal does not name; estimate it or compare with an authenticator app", "location": "specs/PROJ-123-add-login/proposal.md:14"}'
exo change record <change> --add judges_invoked '{"name": "judge-business", "result": "escalated: JBIZ-1 open"}'
exo change record <change> --add capabilities_used '{"name": "judge-business", "type": "judge", "activation": "auto", "resolution": "paths-injected"}'
```

A finding the person dismisses goes to `dismissed_followups` with its `id`, the judge, the rule and the person's reason, for example "internal tool; the cost is covered by the team budget".
