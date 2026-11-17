# Judge contract

Rules every judge follows: the judges of pack `quality` (`judge-code-reviewer`, `judge-security`, `judge-product`, `judge-business`, `judge-frontend` and `judge-team`), the two blind judges of `judgment-day`, the panel that `excellence-committee` convenes, and the `sdd-judge` subagent that runs any of them. A judge skill cites the sections it uses; when a judge skill and this contract disagree, this contract wins.

## A. Advisory first

- A judge reviews and proposes; it never writes code, edits an artifact or applies its own suggestion. The person, or the agent the person asks, fixes.
- The verdict is advisory too: the person decides. A verdict that is not `APPROVED`, or a gate whose Approval says yes, needs the `tech_lead` role (`governance.roles` in `.exo/config.json`) to accept the risk or send the work back.

## B. Independence

- **Blind to the generator:** judge the artifacts and the code, not the author's explanation. Ignore any reasoning, summary or self-assessment of whoever produced the work.
- **Fresh context:** run in a subagent when the agent has one (`sdd-judge`); otherwise say "no isolation" and do the review as a separate pass after the work is done (`.exo/shared/agent-capabilities.md`).
- **One judge, one set of criteria:** review only by your judge's criteria. Other judges cover the rest. Reuse the criteria of the skills your judge names (`security-code-review`, `threat-modeling`, `harness-review`, `product-discovery`, `accessibility-audit`, `frontend-design`); do not invent new ones.

## C. No cascade

Validate against the stage before, in the change root under `specs/`:

| Under review | Validate against |
|---|---|
| proposal.md | The request, the exploration when there is one, and `.exo/context.md` |
| spec.md | The proposal |
| design.md | The proposal and the spec |
| canvas.md | The proposal, the spec and design.md |
| tasks.md | The spec and the design |
| The diff | The spec, the design and the tasks |

A defect that comes from an earlier stage is a finding against that stage, named as such; do not judge a design by a spec the design never received.

## D. Findings

Each finding has:

| Field | Rule |
|---|---|
| `id` | `J<judge code>-<n>`, unique in the change. Never reuse a number. The codes are in the table below. |
| `severity` | Critical (data loss, a security hole, the main flow broken), High (a requirement or scenario not met, a mitigation missing), Medium (an edge case or error path), Low (readability, naming). For an artifact before code (a proposal, a spec, a plan), High means it misses something the next stage needs, and Critical means it would build the wrong thing. |
| `location` | `path:line` when it points at code |
| `rule` | The rule, OWASP or WCAG item, requirement ID or scenario ID it breaks. An OWASP item always carries its edition, because the numbers moved between editions (`OWASP A03:2021` and `OWASP A05:2025` are both Injection): the `security` pack and the judges that reuse it cite the Top 10:2021; the scanners and reviewers of the stack packs, the Top 10:2025, taking the category of each CWE from `.exo/shared/owasp-2025.md`, which also gives the 2021 equivalent. |
| `summary` | What is wrong, and a suggested fix as text |

| Code | Judge |
|---|---|
| `JCR` | `judge-code-reviewer` |
| `JSEC` | `judge-security` |
| `JPRD` | `judge-product` |
| `JBIZ` | `judge-business` |
| `JFE` | `judge-frontend` |
| `JTEAM` | `judge-team` |
| `J4R` | `review-4r`, when its findings are recorded in a change |

`excellence-committee` keeps the code of the judge that raised each finding; its moderator adds no codes of its own. `review-4r` numbers its lens findings `R<n>-<k>` while it works and records the ones that survive as `J4R-n`.

Never copy secrets or personal data into a finding: point at the location. Secrets or personal data written to logs, responses or error messages are at least High, for every judge.

## E. Verdict

- `APPROVED` when no finding is Critical or High.
- `ESCALATED` when one is, when the work contradicts the stage before it, or when the judge could not review something it needed (say what in `Not reviewed`).

## F. Recording

The orchestrator, or the agent when there is none, records the outcome; the judge itself writes nothing.

- **Each finding as a followup**, in `<change-root>/followups.json` (schema `.exo/shared/schemas/followups.schema.json`, severity in lowercase):

  ```bash
  exo change record <change> --followup '{"id": "JSEC-1", "judge": "judge-security", "rule": "CWE-208", "severity": "high", "summary": "The reset token is compared with ==, which leaks timing; use a constant-time comparison such as hmac.compare_digest", "location": "src/auth/reset.py:42"}'
  ```

- **The judge and its verdict** in the AI Usage Record: `--add judges_invoked '{"name": "judge-security", "result": "escalated: JSEC-1 open"}'`, and the judge in `capabilities_used` with `"type": "judge"`.
- **A fixed followup:** once the fix is in, `exo change record <change> --fixed <id>`.
- **A dismissed followup** (the person decides not to fix it) goes to `dismissed_followups` with its `id`, `judge`, `rule` and the person's reason. Never dismiss one on your own.
- Judges have no gate of their own: the gates come from the skills in `.exo/shared/phase-skill-map.md`, Gates.
