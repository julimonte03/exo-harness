# Postmortem template

Copy this into the postmortem file and fill every section. A section with nothing to say keeps its heading and says why. Blameless: roles, never names; what the system allowed, never who failed.

```markdown
# Postmortem: <short title>

- **Incident:** <the incident ID the team uses, if any>
- **Severity:** SEV<n> (<the organization's label, if different>)
- **Date:** YYYY-MM-DD
- **Duration:** <start> to <end> UTC (<minutes> minutes of impact)
- **Status:** draft | in review | final
- **Postmortem owner:** <role>

## Summary

Two or three sentences: what users saw, for how long, what caused it, how it was fixed.

## Impact

- Users or requests affected: <number or share, and how it was measured>
- Journeys affected: <checkout, sign in, ...>
- Data: <none lost | what was affected and how it was repaired>
- Error budget consumed: <share of the period's budget, from the SLO>
- Contractual or customer exposure: <none | what>

## Timeline (UTC)

| Time | Event |
|---|---|
| 14:03 | Deploy of checkout-api v2.41.0 completes |
| 14:05 | Alert fires |
| 14:09 | SEV2 declared |
| 14:19 | Rollback approved and started |
| 14:32 | Mitigated |
| 15:05 | Resolved |

## Detection

How it was noticed (alert, user report, someone looking at a dashboard), the time to detect, and whether an alert should have fired earlier.

## Response

What helped and what slowed the response: access, runbooks, dashboards, people available, tooling.

## Root cause and contributing factors

The trigger, the chain of causes with evidence, why it was not caught earlier, and why the impact was as large as it was. Written with the root-cause-5whys skill when it is installed.

## What went well

## What went badly

## Where we got lucky

## Actions

| ID | Action | Cause | Type | Owner (role) | Due | Check | Ticket |
|---|---|---|---|---|---|---|---|
| A-1 | Add a contract test between checkout-api and the payments schema | Schema change shipped without a consumer test | prevent | payments tech lead | YYYY-MM-DD | The test fails on a branch that renames the column | <ID given by the person> |
| A-2 | Alert on 5xx ratio per release version | Detection took 2 minutes only because traffic was high | detect | on-call lead | YYYY-MM-DD | GameDay: a faulty canary pages within 5 minutes | <ID> |

Cause: the root cause or the finding the action addresses. Types: prevent (removes the cause), detect (catches it earlier), mitigate (reduces the impact), process (changes how people work); prefer prevent and detect. Check: what proves it is done. Ticket: the ID the person gives, or `none`. Every actions table of the ops pack uses these columns.

## Follow-up review

Date when the actions are checked, and by whom (role).
```

## Writing guidance

- **Facts with sources.** Every claim in the timeline and the root cause points at a dashboard, a query, a pipeline run, a commit or a document.
- **No blame words.** Replace "X forgot to", "careless", "should have known" with what the system did not provide: a check, a warning, a test, a safer default.
- **Counterfactuals sparingly.** "If the test had existed, the deploy would have failed" is useful as the reason for an action, not as a judgment.
- **Actions are few and verifiable.** Five strong actions beat fifteen vague ones. "Be more careful" and "improve monitoring" are not actions.
- **No secrets or personal data.** Mask excerpts as the prompt-hygiene skill says; refer to customers by role or segment.
