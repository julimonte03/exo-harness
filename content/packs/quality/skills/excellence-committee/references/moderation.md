# excellence-committee: how the moderator consolidates

The moderator turns five or six independent reports into one decision the person can act on. It adds judgment, never findings of its own: a defect no judge raised is not the moderator's to add. If you notice one, tell the person it needs that judge again.

## 1. Collect

- Keep each judge's answer as it came: its Verdict, its Findings table and its Not reviewed section.
- A judge whose envelope says `needs-input` or `blocked` counts as not reviewed for what it could not see.
- Count the findings by judge and severity for the Panel table before you merge anything.

## 2. Check

For each Critical and High finding, and for any finding the person will have to decide on:

- Read the cited `path:line` and the part of the stage before that the finding cites.
- **Confirmed:** the defect is there.
- **Not confirmed:** the code or the artifact shows otherwise (the input is validated one call earlier, the scenario exists under another title). Keep the finding in the report with `not confirmed` and the evidence; the person decides whether it stays.
- **Cannot tell by reading:** only a test run or a person can say. Keep it as is and say what would settle it.

## 3. Deduplicate

| Situation | What to do |
|---|---|
| Same defect, same place, several judges | One item listing every ID. Severity: the highest of them. Criterion: the one of the judge whose area owns the defect (table below), with the others after it. |
| Same place, different defects | Separate items. |
| Same defect in several places, one fix | One item with every location. |
| Same root cause, different symptoms | Separate items, linked in the Moderation column ("same cause as JCR-3"). |

Every ID of a merged item takes the item's severity when it is recorded.

**Which judge owns which defect** (it leads the item; the others stay listed):

| Defect | Owner |
|---|---|
| Exploitable weakness, missing mitigation, secrets or personal data exposed | `judge-security` |
| Wrong behavior, unhandled error, test that does not prove its scenario | `judge-code-reviewer` |
| User, problem, success measure, scope, user flows and states in the spec | `judge-product` |
| Value, cost, risk, alternatives, business metrics, reaching the users | `judge-business` |
| Overlapping files between units, dependencies, size, concentrated knowledge | `judge-team` |
| UI consistency, UI states, client performance and security, accessibility | `judge-frontend` |

## 4. Contradictions

Two judges contradict each other when following one finding's fix makes the other's worse. Common pairs:

| Pair | Typical tension |
|---|---|
| Product and team | More scope for the user; a plan already at its budget |
| Product and security | Less friction (fewer steps, longer sessions); more protection |
| Business and code or security | Ship sooner or cheaper; do it properly first |
| Frontend and business | A new visual style that sells better; consistency with the design system |

For each one:

1. State both positions in one line each, with their IDs.
2. Recommend, with the reason, using this order of precedence: the law and the data protection rules (`.exo/shared/data-protection.md`); security; the requirements of the spec and the proposal's promise to its user; the plan's budget; convenience and speed.
3. Offer the way out that keeps both when there is one: a follow-up change, a feature flag, a smaller first version.
4. Mark it as a decision for the person. A contradiction does not change the verdict by itself; the severities of its findings do.

## 5. Calibrate

Adjust only with a reason written as `from → to: why`. Allowed:

| Adjustment | When |
|---|---|
| Raise one level | Several judges trace the same root cause; or the finding blocks the main flow more than its judge could see from its angle |
| Raise to High | A Medium that, once merged, leaves a requirement or a promised flow unmet |
| Lower one level | The finding is speculative (no path reaches it), outside the target (pre-existing and untouched by the change), or handled where its judge could not see (cite the `path:line` that handles it) |

Never:

- lower a finding about secrets or personal data below High (`.exo/shared/judge-common.md`, section D);
- lower a Critical security finding at all;
- change a severity to reach a verdict you prefer.

Only the person, with the `tech_lead` role when the verdict is not `APPROVED`, accepts a risk the moderator may not lower.

## 6. Verdict

- `APPROVED`: after moderation, no consolidated finding is Critical or High, and no judge left unreviewed something it needed.
- `ESCALATED`: otherwise. Write the reason in one line: the IDs that stay Critical or High, or what was not reviewed.
- When a judge escalated only because its input was missing outside a change (no purpose, no plan), say so: "ESCALATED: judge-business could not review the value; give the purpose and run the committee again."

## 7. Order of the report

1. Verdict, with its one-line reason.
2. Panel: every judge, convened or not, with what it reviewed, its isolation, its own verdict and its counts.
3. Consolidated findings, Critical first, then High, Medium and Low; within a severity, confirmed before not confirmed.
4. Contradictions, each with the recommendation and "the person decides".
5. Severity adjustments, each as `from → to: why`.
6. Not reviewed, merged from every judge, with what would let it be reviewed.
