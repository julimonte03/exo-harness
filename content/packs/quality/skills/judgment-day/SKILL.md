---
name: judgment-day
description: >-
  Runs the mandatory final review of a Tier 4 change after verify: two blind
  judges in parallel (judge-code-reviewer and judge-security), confirmed
  findings fixed by whoever implemented the change, and a new round of
  judging, up to three rounds, until the outcome is APPROVED or ESCALATED to
  the person. Records every confirmed finding as a followup and the outcome
  in the AI Usage Record, which exo check requires in Tier 4; the person
  approves explicitly. Use it when a Tier 4 change has a ready verify, when
  exo change status says the next phase is judgment, or when the person asks
  for a judgment day. Triggers: "judgment day", "run judgment day", "final
  review", "adversarial review", "blind judges", "approve the Tier 4 change".
metadata:
  exo-pack: quality
  exo-execution: inline
  exo-phase: judgment
  exo-permissions: read-only+record
---

# judgment-day

## Result

- Up to three rounds, each with two independent findings reports (`JCR-n` and `JSEC-n`), the confirmed findings, and the fixes made by whoever implemented the change.
- An outcome: `APPROVED` (no confirmed Critical or High finding left open) or `ESCALATED` (one is still open after the third round, or the person did not approve).
- Every confirmed finding in `<change-root>/followups.json`, and the outcome in the AI Usage Record. `exo check` and `exo change status` accept a Tier 4 change only with `{"name": "judgment-day", "result": "approved"}` in `judges_invoked`: exactly the string `approved`, recorded after the person's explicit approval. Any other text (`APPROVED`, `approved with notes`) does not count.

## When

- **Tier 4, always,** after a verify whose Verdict is `ready`: `exo change status <change> --json` gives `next_phase: judgment`, and `sdd-archive` does not run without an approved judgment day.
- A verify that is not `ready`, or no Judgment Day Handoff: stop with `status: blocked` and `next: verify`.
- Automatic mode stops here too (`.exo/shared/sdd-phase-common.md`, section H): only the person approves.
- In a lower tier the person may ask for it; it is then advisory, and nothing requires it.

## Who does what

| Role | Who | Writes |
|---|---|---|
| Coordinator (this skill) | the orchestrator's session, or the agent when there is none | only the record, with `exo change record` |
| Judges | skill:judge-code-reviewer and skill:judge-security, each in its own `sdd-judge` | nothing: their findings come back in their answers |
| Fixer | whoever implemented the change: `sdd-apply` in `sdd-implementer` | code and tests, inside the plan |
| Verifier | `sdd-verify` in `sdd-verifier` | `verify-record.md` and the gates, through the orchestrator |
| Approver | the person; for an `ESCALATED` outcome, the `tech_lead` role | their decision, which you record |

The judges never fix. As coordinator you do not fix either: you coordinate, consolidate and record, and the fix goes through `sdd-apply` (run inline when the agent has no subagents). `.exo/shared/judge-common.md` rules everything about the judges.

## Start: the handoff

1. Read `verify-record.md`, section Judgment Day Handoff: the riskiest files, the risks of `design.md` to check again, and what the verifier could not verify. `N/A` or empty in Tier 4 means the verify is incomplete: stop with `next: verify`.
2. Gather what the judges will read: `spec.md`, `design.md` (Risks & Mitigations), `tasks.md`, `test-spec.md` and the diff (`git diff <base>...HEAD`). `sdd-judge` cannot run git: pass the diff text, or the list of changed files when the diff is too long.
3. Take the next free number of each prefix from `exo change followups <change> --status all`.

## A round

### 1. Two blind judges, in parallel

Launch both delegations to `sdd-judge` at the same time, one per judge, with the prompt in `references/judge-prompt.md`: the judge's `SKILL.md` path (for `judge-security`, also the one of `security-code-review` when it is installed), the change, the handoff, the files to read and the next free ID.

- **Never in the prompt:** the other judge's findings, the implementer's reasoning or explanation of a fix, or your own opinion. Each judge is blind to the generator and to the other judge.
- **From the second round:** each judge gets only its own open findings from the round before, with their IDs, and says which ones are resolved.
- **Without subagents:** two separate passes inline, one per judge, each with only its criteria and reading the files again from disk. Finish and write down the first pass before you start the second, and say `no isolation` in the round report, the record and the envelope.

### 2. Consolidate

- **Confirmed:** a defect that both judges report (the same problem at the same place, whatever their IDs), or one that a single judge reports and a new check confirms. The check: read the cited `path:line` and the stage it cites; when only a test can tell, ask `sdd-verifier` to run that test, or run it yourself without subagents; nothing changes.
- **Not confirmed:** the check shows the defect is not there. Show it to the person with the reason, and keep it if the person says so. Never drop one silently.
- When both judges report the same defect, keep both findings (each with its judge, ID and rule) and fix it once. When they disagree on the severity, take the higher one.

### 3. Record and decide

Record each confirmed finding as a followup. Severity goes in lowercase; the command validates the entry and rejects an `id` already in use with other content.

```bash
exo change record <change> --followup '{"id": "JSEC-1", "judge": "judge-security", "rule": "OWASP A01:2021", "severity": "high", "summary": "The export does not check that the account belongs to the caller; load it through the session", "location": "src/export/views.py:31"}'
```

Show the person the confirmed findings, by severity:

- **Critical and High** get fixed (step 4), or stay open and count toward escalation.
- **Medium and Low:** the person decides, for each one, to fix it or to dismiss it. A dismissal goes to `dismissed_followups` with its `id`, `judge`, `rule` and the person's reason. Never dismiss one on your own.

`followups.json` keeps every finding. When a fix is in, mark it with `exo change record <change> --fixed <id>`: `exo change followups <change>` then lists only what is still open.

### 4. Fix and verify again

- The fix goes to whoever implemented the change: `sdd-apply` in `sdd-implementer`, with the accepted findings as its input, inside the plan. It runs the tests.
- A fix that needs to change the spec or the design is outside the plan: stop with `status: blocked` and, as `next`, the phase that owns that artifact.
- Then `sdd-verify` runs again, so that `verify-record.md` and the gates describe the final code. The next round starts from its new Judgment Day Handoff.

### When the loop ends

- **Nothing confirmed is left to fix** (nothing Critical or High, and the person dismissed the rest): the outcome is `APPROVED`.
- **Something to fix in round 1 or 2:** step 4, then a new round.
- **Round 3 with a confirmed Critical or High finding:** the outcome is `ESCALATED`. There is no fourth round, and you do not fix it inside this judgment day.
- **Round 3 with only Medium or Low findings to fix:** step 4, and the outcome is `APPROVED`; the verify that runs after the fix covers them.

## Outcome and approval

- **APPROVED:** show the rounds, the fixed findings and the dismissed ones, and ask: "Judgment day ends with no open Critical or High finding. Do you approve this change for archive?" Only an explicit yes counts; then record `approved`. If the person says no, record `escalated: <their reason>`, and the change goes back where they say.
- **ESCALATED:** tell the person which findings stay open, by ID and severity, and that the decision needs the `tech_lead` role. Record `escalated: <why>`. Then either:
  - the `tech_lead` accepts the risk: each open finding goes to `dismissed_followups` with their reason, a decision is recorded with `"by": "human"`, and then `approved`; or
  - the work goes back to `sdd-apply`, or to the phase that owns the wrong artifact, and a new judgment day runs after the next ready verify.
- The engine does not check roles: CODEOWNERS and branch protection make the `tech_lead` approval effective (`.exo/shared/ci-and-review.md`, section E).
- In an unattended run, never approve on the person's behalf: leave the outcome open, say so, and stop.

## Record

The judges write nothing; you record, as `.exo/shared/judge-common.md` (section F) and `.exo/shared/capability-attribution.md` say. In Windows PowerShell 5.1, pass each JSON as `@<file>` (`.exo/shared/sdd-phase-common.md`, section I).

```bash
exo change record <change> --add capabilities_used '{"name": "judgment-day", "type": "skill", "activation": "auto", "resolution": "fallback-registry"}'
exo change record <change> --add capabilities_used '{"name": "sdd-judge", "type": "subagent", "activation": "auto"}'
exo change record <change> --add capabilities_used '{"name": "judge-code-reviewer", "type": "judge", "activation": "auto", "resolution": "paths-injected"}'
exo change record <change> --add capabilities_used '{"name": "judge-security", "type": "judge", "activation": "auto", "resolution": "paths-injected"}'
exo change record <change> --add judges_invoked '{"name": "judge-code-reviewer", "result": "round 2: JCR-1 fixed, no new findings"}'
exo change record <change> --add judges_invoked '{"name": "judge-security", "result": "round 2: JSEC-1 fixed"}'
exo change record <change> --add decisions '{"summary": "Judgment day approved after 2 rounds", "by": "human"}'
exo change record <change> --add judges_invoked '{"name": "judgment-day", "result": "approved"}'
exo change record <change> --add skills_used '"judgment-day"'
exo change record <change> --phase-done judgment
```

- An escalated outcome: `--add judges_invoked '{"name": "judgment-day", "result": "escalated: JSEC-1 (High) open after 3 rounds"}'`. Entries add up: a later `approved` from the `tech_lead` does not erase the escalation.
- `--phase-done judgment` only with the approval, when the envelope says `status: ok`.
- Then `exo check --change <change>` no longer reports the missing judgment day.

## End

| Outcome | `status` | `next` |
|---|---|---|
| Approved by the person | `ok` | `archive` |
| Escalated, or waiting for the person | `needs-input` | `judgment` |
| A fix outside the plan | `blocked` | the phase that owns the artifact |
| Verify not ready, or no handoff | `blocked` | `verify` |

```yaml
status: ok
phase: judgment
change_name: PROJ-123-add-login
artifacts:
  - path: specs/PROJ-123-add-login/followups.json
    summary: "3 confirmed findings: 2 fixed (JCR-1, JSEC-1), 1 Low dismissed by the person"
notes: >-
  Isolation: judges in sdd-judge subagents, blind to each other.
  Rounds: 2. Outcome: APPROVED, approved by the person.
next: archive
```

Outside an SDD change, the person may ask for a judgment day on a branch: the same rounds against the target branch, with the findings and the outcome in the answer and nothing recorded.
