# Judge contract

Rules every judge follows: `judge-code-reviewer` and `judge-security` (pack `quality`), the two blind judges of `judgment-day`, and the `sdd-judge` subagent that runs any of them. A judge skill cites the sections it uses; when a judge skill and this contract disagree, this contract wins.

## A. Advisory first

- A judge reviews and proposes; it never writes code, edits an artifact or applies its own suggestion. The person, or the agent the person asks, fixes.
- The verdict is advisory too: the person decides. A verdict that is not `APPROVED` needs the `tech_lead` role (`governance.roles` in `.exo/config.json`) to accept the risk or send the work back.

## B. Independence

- **Blind to the generator:** judge the artifacts and the code, not the author's explanation. Ignore any reasoning, summary or self-assessment of whoever produced the work.
- **Fresh context:** run in a subagent when the agent has one (`sdd-judge`); otherwise say "no isolation" and do the review as a separate pass after the work is done (`.exo/shared/agent-capabilities.md`).
- **One judge, one set of criteria:** review only by your judge's criteria. Other judges cover the rest. Reuse the criteria of the skills your judge names (`security-code-review`, `threat-modeling`, `harness-review`); do not invent new ones.

## C. No cascade

Validate against the stage before, in the change root under `specs/`: the proposal and the spec for a design, the design for a plan, the spec, the design and the tasks for a diff. A defect that comes from an earlier stage is a finding against that stage, named as such; do not judge a design by a spec the design never received.

## D. Findings

Each finding has:

| Field | Rule |
|---|---|
| `id` | `J<judge code>-<n>`, unique in the change: `JCR-1` for `judge-code-reviewer`, `JSEC-1` for `judge-security`. Never reuse a number. |
| `severity` | Critical (data loss, a security hole, the main flow broken), High (a requirement or scenario not met, a mitigation missing), Medium (an edge case or error path), Low (readability, naming) |
| `location` | `path:line` when it points at code |
| `rule` | The rule, OWASP or WCAG item, requirement ID or scenario ID it breaks |
| `summary` | What is wrong, and a suggested fix as text |

Never copy secrets or personal data into a finding: point at the location.

## E. Verdict

- `APPROVED` when no finding is Critical or High.
- `ESCALATED` when one is, when the work contradicts the stage before it, or when the judge could not review something it needed (say what in `Not reviewed`).

## F. Recording

The orchestrator, or the agent when there is none, records the outcome; the judge itself writes nothing.

- **Each finding as a followup**, in `<change-root>/followups.json` (schema `.exo/shared/schemas/followups.schema.json`, severity in lowercase):

  ```bash
  exo change record <change> --followup '{"id": "JSEC-1", "judge": "judge-security", "rule": "OWASP A07:2021", "severity": "high", "summary": "Password compared with ==; use a constant-time comparison", "location": "src/auth/login.py:42"}'
  ```

- **The judge and its verdict** in the AI Usage Record: `--add judges_invoked '{"name": "judge-security", "result": "escalated: JSEC-1 open"}'`, and the judge in `capabilities_used` with `"type": "judge"`.
- **A dismissed followup** (the person decides not to fix it) goes to `dismissed_followups` with its `id`, `judge`, `rule` and the person's reason. Never dismiss one on your own.
- **A gate run by a judge** also writes its `<change-root>/gates/<gate>.md` from `.exo/shared/templates/gate.md`.
