---
name: excellence-committee
description: >-
  Convenes the panel of advisory judges on a change, a diff or a set of
  artifacts, on request: judge-code-reviewer and judge-security always;
  judge-product and judge-business when there is a proposal or a stated
  purpose; judge-team when there is a plan; judge-frontend when there is UI;
  each as an independent read-only review in its own sdd-judge subagent. Then a
  moderator consolidates their findings: removes duplicates, settles
  contradictions, calibrates severities with stated reasons and gives one
  verdict. Findings keep the code of the judge that raised them. Inside an
  SDD change it records the outcome; outside, it only reports. Not part of
  the phase map. Use it when someone wants every angle reviewed at once
  before a big decision. Triggers: "excellence committee", "convene all the
  judges", "full panel review", "review board", "review this from every
  angle", "all the judges at once", "multi-lens review board".
metadata:
  exo-pack: quality
  exo-execution: inline
  exo-permissions: read-only+record
---

# excellence-committee

## Result

- One consolidated report: the panel (who reviewed what, how isolated, each judge's verdict), the consolidated findings by severity with the IDs of the judges that raised them, the contradictions and how the moderator settled them, the severity adjustments with their reasons, what was not reviewed, and one verdict: `APPROVED` or `ESCALATED`.
- Inside an SDD change: each finding in `followups.json` and the outcome in the AI Usage Record, as `.exo/shared/judge-common.md`, section F, says. Outside a change: the report only; nothing is written.
- Nothing is fixed. The committee advises; the person decides.

## When

- **On request only:** someone wants every angle on a change, a diff, a branch or a set of artifacts before a big decision (a release, a launch, a hard-to-reverse design, a risky merge).
- It is not in the phase map, owns no gate, and replaces neither the judges of each phase nor skill:judgment-day in Tier 4.
- **Not for:** a check before committing (skill:pre-commit-review), the review of verify (skill:harness-review), the final Tier 4 review (skill:judgment-day), or a single angle (call that judge directly).
- It costs up to six reviews plus a moderation. When the target is small, say so and offer the one judge that fits.

## Contract

`.exo/shared/judge-common.md` rules every judge of the panel and the panel itself: advisory first (A), independence (B), no cascade (C), findings (D), verdict (E) and recording (F). The moderator keeps the code of the judge that raised each finding and adds no codes of its own.

## Roles

| Role | Who | Writes |
|---|---|---|
| Coordinator and moderator (this skill) | the session the person talks to | nothing outside a change; inside one, only the record, with `exo change record` |
| Judges | skill:judge-code-reviewer, skill:judge-security, skill:judge-product, skill:judge-business, skill:judge-team and skill:judge-frontend, each in its own `sdd-judge` | nothing: their findings come back in their answers |
| Fixer | the person, or the agent they ask, after the committee | the fixes, outside this skill |

You coordinate and moderate; you never judge in a judge's place, and no judge sees another's findings.

## Permissions

Read-only: read files, `git status`, `git diff`, `git log`, `exo change status` and `exo change followups`. Inside a change, also `exo change record`. Never edit, stage, commit or fix anything, not even a finding you agree with.

## 1. Scope the review

1. **The target:**
   - an SDD change: `exo change status <change> --json` gives the root, the tier, the phase and the artifacts;
   - a branch or a PR: the target branch as base, and `git diff <base>...HEAD`;
   - uncommitted work: `git diff` and `git status` (new files are read in full);
   - artifacts the person points at.
2. **The panel,** each judge with what it reviews and against what (`.exo/shared/judge-common.md`, section C):

   | Judge | Reviews | Against | Convened |
   |---|---|---|---|
   | `judge-code-reviewer` | `design.md`, or the diff | the stage before | always |
   | `judge-security` | `design.md`, or the diff | the stage before | always |
   | `judge-product` | `proposal.md` and `spec.md`, or the purpose the person gives (who it is for, which problem) | the request | only with a proposal, a spec or a stated purpose |
   | `judge-business` | `proposal.md`, or the purpose the person gives | the goals in `.exo/context.md` and the request | only with a proposal or a stated purpose |
   | `judge-team` | `tasks.md`, or the plan or breakdown the person gives | `spec.md` and `design.md`, or the purpose | only with a plan |
   | `judge-frontend` | the UI of `design.md`, or the UI files of the diff | the stage before | only when the change touches UI, as that judge defines it |

   A diff alone gives `judge-product`, `judge-business` and `judge-team` nothing to judge: their criteria are for a proposal, a spec or a purpose, and for a plan. A judge without its input is not convened: the panel table lists it as `not convened: no plan` (or `no purpose`), and Not reviewed says what it would need.

3. **What the panel needs:** inside a change, the artifacts are there. Outside, ask the person once, in one message, for what is missing: the purpose (who it is for, which problem, why now) and the plan, if there is one. When they have none, the judges that need them are not convened (step 2), and you go on with the rest.
4. **IDs:** inside a change, the next free number of each prefix from `exo change followups <change> --status all`; outside, every prefix starts at 1.
5. **The diff text:** `sdd-judge` cannot run git. Get the diff yourself and pass its text, or the list of changed files when it is too long.

## 2. Convene the panel

- **One read-only delegation to `sdd-judge` per judge, all launched at the same time,** with the prompt in `references/panel-prompt.md`: the judge's `SKILL.md` path under `## Skills to load before work`, plus the skills that judge reuses when they are installed (`security-code-review` for `judge-security`, `product-discovery` for `judge-product`, `accessibility-audit` and `frontend-design` for `judge-frontend`); the target, the stage before, and the first free ID.
- **Never in a prompt:** another judge's findings, the author's explanation or self-assessment, your own opinion, or what you expect the judge to find.
- **The judges ship in this pack.** A judge missing from the registry means an incomplete installation: say so, suggest `exo doctor`, and run it with its inline criteria from `.exo/shared/phase-skill-map.md`, keeping the sentence `quality/<judge> not installed — applying inline criteria`. The skills a judge reuses degrade inside that judge, as its own skill says.
- **Without subagents,** or without `sdd-judge` (it ships in the `sdd` pack): run each judge inline, one at a time, as a separate pass with only its criteria, reading the files again from disk. Write down each pass's findings before you start the next, and say "no isolation" in the report. Moderate only when every pass is written down.
- **A judge that answers `needs-input`:** give it what it asks for when you have it, or ask the person; otherwise its part goes to Not reviewed.

## 3. Moderate

Once every judge has answered. The full rules are in `references/moderation.md`; in order:

1. **Collect** each findings table, verdict and Not reviewed section as returned. Never rewrite a judge's finding: the moderation is a layer on top.
2. **Check** each Critical and High finding: read the cited `path:line` and the stage it cites. One the check does not support stays in the report, marked `not confirmed` with the reason. Never drop a finding silently.
3. **Deduplicate:** the same defect at the same place, raised by several judges, becomes one consolidated item that lists every ID (`JSEC-2, JFE-1`), takes the highest of their severities, and is led by the criterion of the judge whose area owns it.
4. **Settle contradictions:** when two judges ask for opposite things (more scope and a smaller plan; more friction for security and less for the user), name both, give your recommendation with its reason, and leave the decision to the person. Security, data protection and the requirements of the spec win over convenience unless the person decides otherwise.
5. **Calibrate severities,** each adjustment with its reason and as `from → to`: raise when several judges point at one root cause or a finding blocks the main flow; lower when a finding is speculative, outside the target, or already handled where its judge could not see. Never lower a finding about secrets or personal data below High, nor any Critical security finding: only the person accepts those.
6. **Verdict:** `APPROVED` when no consolidated finding is Critical or High and no judge left unreviewed something it needed; `ESCALATED` otherwise, with the reason in one line. A verdict that is not `APPROVED` needs the `tech_lead` role to accept the risk or send the work back.

## Report

```markdown
# Excellence Committee: PROJ-123-add-login

## Verdict

ESCALATED: JSEC-1 (High) stays open. One contradiction needs the person's decision.

## Panel

| Judge | Reviewed | Isolation | Verdict | Critical / High / Medium / Low |
|---|---|---|---|---|
| judge-code-reviewer | the diff, against spec.md, design.md and tasks.md | sdd-judge | APPROVED | 0 / 0 / 1 / 0 |
| judge-security | the diff, against design.md (Risks & Mitigations) | sdd-judge | ESCALATED | 0 / 1 / 0 / 1 |
| judge-product | proposal.md and spec.md | sdd-judge | APPROVED | 0 / 0 / 1 / 1 |
| judge-business | proposal.md | sdd-judge | APPROVED | 0 / 0 / 0 / 1 |
| judge-team | tasks.md, against spec.md and design.md | sdd-judge | APPROVED | 0 / 0 / 1 / 0 |
| judge-frontend | not convened: no UI in the change | - | - | - |

## Consolidated findings

| Severity | IDs | path:line | Finding | Criterion | Suggested fix | Moderation |
|---|---|---|---|---|---|---|
| High | JSEC-1 | src/auth/reset.py:42 | The reset token is compared with ==, which leaks timing | CWE-208 | Use a constant-time comparison | confirmed |
| Medium | JSEC-2, JCR-1 | src/auth/login.py:57 | The sign-in error says whether the email exists | CWE-204, A07:2025 Authentication Failures | One message for a wrong email and a wrong password | duplicate; Medium from JCR-1 |
| Medium | JPRD-2, JBIZ-1 | specs/PROJ-123-add-login/proposal.md:9 | The success measure has no baseline | product-discovery: success measure; rubric 6 | Give today's weekly failed sign-ins | duplicate; raised Low → Medium |
| Medium | JPRD-1 | specs/PROJ-123-add-login/proposal.md:14 | "Remember me" is out of scope, though the problem cites users who sign in many times a day | scope | Bring it into the scope | contradicts JTEAM-1 |
| Medium | JTEAM-1 | specs/PROJ-123-add-login/tasks.md:3 | The plan is already at its 400-line budget | rubric 4: reasonable size | Keep new scope for a follow-up change | contradicts JPRD-1 |

## Contradictions

- JPRD-1 asks to bring "remember me" into the scope; JTEAM-1 says the plan is already at its budget. Recommendation: a follow-up change, so this one stays reviewable. The person decides.

## Severity adjustments

- JPRD-2 and JBIZ-1: Low → Medium, because two judges trace the same missing baseline, and without it neither the user's nor the business's success can be checked.

## Not reviewed

None.
```

Every finding of every judge appears in Consolidated findings, alone or merged; the panel table lists every judge, convened or not, with the reason.

## Record

Inside an SDD change only, as `.exo/shared/judge-common.md`, section F, and `.exo/shared/capability-attribution.md` say. Outside a change, record nothing. In Windows PowerShell 5.1, pass each JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

```bash
exo change record <change> --followup '{"id": "JSEC-1", "judge": "judge-security", "rule": "CWE-208", "severity": "high", "summary": "The reset token is compared with ==, which leaks timing; use a constant-time comparison", "location": "src/auth/reset.py:42"}'
exo change record <change> --add judges_invoked '{"name": "judge-security", "result": "escalated: JSEC-1 open"}'
exo change record <change> --add judges_invoked '{"name": "excellence-committee", "result": "escalated: JSEC-1 open; 1 contradiction for the person"}'
exo change record <change> --add capabilities_used '{"name": "excellence-committee", "type": "skill", "activation": "requested", "resolution": "fallback-registry"}'
exo change record <change> --add capabilities_used '{"name": "sdd-judge", "type": "subagent", "activation": "auto"}'
exo change record <change> --add capabilities_used '{"name": "judge-security", "type": "judge", "activation": "auto", "resolution": "paths-injected"}'
exo change record <change> --add skills_used '"excellence-committee"'
```

- **Each finding** under its own ID and judge, merged ones too, with the moderated severity in lowercase; when you adjusted it, say so in the summary (`raised from low: same missing baseline as JBIZ-1`). A finding marked `not confirmed` is recorded only if the person keeps it.
- **Each judge** in `judges_invoked` and in `capabilities_used` with `"type": "judge"`; the committee once more with the consolidated verdict.
- **Never** dismiss a finding yourself: the person decides, and the dismissed ones go to `dismissed_followups` with their reason. Fixed ones are marked later with `--fixed <id>`.
- The committee is not a phase: no `--phase-done`.

## Before you finish

- Every judge was convened, or the panel table says why not.
- No prompt carried another judge's findings or the author's explanation.
- Every finding is in the report, alone or merged; none dropped silently.
- Each merge, adjustment and contradiction has its reason, and the verdict follows the rule.
- Nothing was edited; inside a change, everything is recorded; outside, nothing is.
