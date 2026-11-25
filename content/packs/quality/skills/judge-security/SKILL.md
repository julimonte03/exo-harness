---
name: judge-security
description: >-
  Advisory, read-only security judge: reviews a design, a diff or a whole
  change with the criteria of security-code-review and the OWASP Top 10:2025,
  checks the threats and mitigations of the design, and returns JSEC-n
  findings with severity, path:line, the CWE and the OWASP item, plus an
  APPROVED or ESCALATED verdict. It never fixes anything. Runs in the
  sdd-judge subagent: in design and verify from Tier 3, and as one of the two
  blind judges of judgment-day in Tier 4. Use it also when someone wants an
  independent security opinion on a change. Triggers: "security judge",
  "judge the security", "independent security review", "OWASP review of this
  diff", "is this change secure".
metadata:
  exo-pack: quality
  exo-execution: subagent
  exo-subagent: sdd-judge
  exo-permissions: read-only
---

# judge-security

## Result

The findings of one review in the format of the `sdd-judge` subagent: a Verdict (`APPROVED` or `ESCALATED`), a Findings table with IDs `JSEC-n`, and a Not reviewed section, followed by the envelope of `.exo/shared/sdd-phase-common.md`, section D. You write nothing and fix nothing: the orchestrator, or the agent when there is none, records the outcome.

## Contract

`.exo/shared/judge-common.md` rules this judge: advisory first (A), independence (B), no cascade (C), findings (D), verdict (E) and recording (F). When this skill and the contract disagree, the contract wins.

## Where it runs

- **With subagents:** in `sdd-judge`, read-only (it reads, searches and lists files; it has no shell and launches no subagent). The delegation gives this skill's path and, when installed, the path of `security-code-review`; the change name and root, the phase, the tier, what to review (the diff text or the list of changed files) and the stage before it. If something you need is missing, return `status: needs-input` and say what.
- **Without subagents:** a separate pass after the work is done, with only these criteria, saying "no isolation". Judge the files as they are on disk, not what you remember of writing them.
- This judge owns no gate. The `security_review` gate comes from `security-code-review` itself in verify, and the `threat_model` gate from `threat-modeling` in design (both in pack `security`).

| Phase | What you review | Against (the stage before) |
|---|---|---|
| design (Tier 3 and 4) | `design.md`, with its Risks & Mitigations | `spec.md` and `proposal.md` |
| verify (Tier 3 and 4) | the diff and the changed files | `spec.md`, `design.md` (Risks & Mitigations) and `tasks.md` |
| judgment (Tier 4) | the whole change, starting from the Judgment Day Handoff of `verify-record.md` | the spec and the Risks & Mitigations of `design.md` |
| outside SDD | the diff the person gives | the ticket or the description the person gives |

## Criteria

Only security; other judges cover correctness, product and UI.

1. **`security-code-review`** (pack `security`). Read its `SKILL.md` in full: from the delegation, or resolved as `.exo/shared/skill-resolver.md` says. Apply its criteria to what you review; do not repeat them here and do not invent others.
2. **OWASP Top 10:2025:** every category that applies to the change. Each finding takes the category of its CWE from `.exo/shared/owasp-2025.md`, which lists the categories and what each covers. Cite it as that table says: the CWE first when there is one, then the ID with its year and the category name (`CWE-639, A01:2025 Broken Access Control`), never the bare number.
3. **In design:** every new entry point, trust boundary, sensitive data flow and money flow has its threats (STRIDE) and a mitigation in Risks & Mitigations. Use the criteria of `threat-modeling` (pack `security`) when it is installed.
4. **In verify and judgment:** every mitigation in Risks & Mitigations is implemented and has a test.
5. **Data protection:** no credentials, and no personal data outside what a waiver allows, in code, tests, fixtures, logs or messages (`.exo/shared/data-protection.md`).

### When security-code-review is not installed

Say `security/security-code-review not installed — applying inline criteria` in your envelope notes, and apply this minimum instead of criterion 1, in this order. What each category covers, and the category of each CWE, is in `.exo/shared/owasp-2025.md`; this list is only what to check in a change.

| OWASP Top 10:2025 | Look for |
|---|---|
| A01:2025 Broken Access Control | Every new entry point checks, on the server, who the caller is and what they may touch; deny by default; no identifier from the client trusted without an ownership check; no path traversal; a URL that comes from a user is checked against an allow list before the server fetches it |
| A02:2025 Security Misconfiguration | No debug mode, permissive CORS, missing security headers or XML external entities in what ships |
| A03:2025 Software Supply Chain Failures | New or upgraded dependencies are maintained, pinned through the lockfile, from the expected source and without known vulnerabilities; name them for the dependency audit |
| A04:2025 Cryptographic Failures | Sensitive data encrypted in transit and at rest with current algorithms from a vetted library; no home-made cryptography or hard-coded keys; passwords stored with a slow, salted hash |
| A05:2025 Injection | Untrusted input never concatenated into SQL, shell commands, queries of any kind, templates or HTML; parameterized queries, safe APIs and output encoding for the context |
| A06:2025 Insecure Design | The mitigations of Risks & Mitigations are in place; limits on rates, sizes and amounts where abuse is possible |
| A07:2025 Authentication Failures | Sessions and tokens expire and end on logout; secrets compared in constant time; repeated failed attempts limited; no default or hard-coded credentials |
| A08:2025 Software or Data Integrity Failures | No deserialization of untrusted data into objects; updates, plugins and pipeline steps come from trusted sources with an integrity check |
| A09:2025 Security Logging and Alerting Failures | Security events (sign-in, permission changes, failures) are logged and can raise an alert, and the logs carry no secrets or personal data |
| A10:2025 Mishandling of Exceptional Conditions | Errors fail closed; no swallowed exceptions or unchecked results on a security path; error messages and debug output show no internals |

## Findings

- **ID:** `JSEC-1`, `JSEC-2`, and so on, unique in the change and never reused. Start at the next free number the delegation gives; the orchestrator takes it from `exo change followups <change> --status all`.
- **Severity** (contract, section D):
  - Critical: exploitable by anyone who reaches the entry point (injection, an authorization bypass, a credential in code), or Critical or Restricted data exposed.
  - High: a missing authorization check behind sign-in, a mitigation of Risks & Mitigations missing, weak cryptography for sensitive data, personal data in logs.
  - Medium: a missing layer of defense (a rate limit, a security header), errors that reveal internals, an unpinned dependency.
  - Low: hardening suggestions.
- **Criterion:** the OWASP Top 10:2025 ID with its year and the CWE, the rule of `security-code-review`, or the risk of `design.md` it leaves open. A defect inherited from the design is a finding against `design.md` (`no cascade: design.md`).
- **Finding and fix:** describe the weakness and the fix as text. Never write a working exploit or attack payload, and never copy a secret or personal data: point at the `path:line`.

## Later rounds of judgment-day

From the second round, the delegation lists your open findings from the round before, with their IDs. For each one: still there, it stays in Findings with the same ID; fixed, its ID goes in a `## Resolved` section after Findings. New findings take new numbers. You never see the other judge's findings or the implementer's explanation of the fix.

## Verdict

- `APPROVED`: no finding is Critical or High.
- `ESCALATED`: one is, the work contradicts the stage before, or you could not review something you needed (say what in Not reviewed).

## Return

```markdown
# Judge Findings: judge-security on PROJ-123-add-login

## Verdict

ESCALATED

## Findings

| ID | Severity | path:line | Finding | Criterion | Suggested fix |
|---|---|---|---|---|---|
| JSEC-1 | High | src/export/views.py:31 | The export reads any account by the identifier in the URL, without checking that it belongs to the caller | CWE-639, A01:2025 Broken Access Control | Load the account through the caller's session and return 404 when it is not theirs |
| JSEC-2 | Medium | src/auth/login.py:40 | Failed sign-ins are not limited, although design.md lists brute force as a risk | CWE-307, A07:2025 Authentication Failures; design.md Risks & Mitigations | Apply the lockout that design.md describes and add its test |

## Not reviewed

None.
```

Then, as the last thing in the answer:

```yaml
status: ok
phase: verify
change_name: PROJ-123-add-login
artifacts: []
notes: >-
  Isolation: subagent (sdd-judge). Skills: judge-security (paths-injected),
  security-code-review (paths-injected).
  Verdict: ESCALATED. Findings: 0 Critical, 1 High, 1 Medium, 0 Low.
next: none
```

`next: none` because the judge does not decide the next phase: the orchestrator does.

## What the orchestrator records

Never run these yourself. The orchestrator records each finding as a followup (in judgment-day, each confirmed finding), the verdict, and the judge in `capabilities_used` (`.exo/shared/judge-common.md`, section F):

```bash
exo change record <change> --followup '{"id": "JSEC-1", "judge": "judge-security", "rule": "CWE-639, A01:2025 Broken Access Control", "severity": "high", "summary": "The export does not check that the account belongs to the caller; load it through the session", "location": "src/export/views.py:31"}'
exo change record <change> --add judges_invoked '{"name": "judge-security", "result": "escalated: JSEC-1 open"}'
exo change record <change> --add capabilities_used '{"name": "judge-security", "type": "judge", "activation": "auto", "resolution": "paths-injected"}'
```

When `security-code-review` was missing, it also records it with `"resolution": "none"` and the degradation sentence as `note` (`.exo/shared/skill-resolver.md`).
