---
name: security-code-review
description: >-
  Reviews a diff for security vulnerabilities, read-only: injection, broken
  authentication and authorization, exposed secrets, unsafe deserialization,
  SSRF, path traversal, XSS, risky dependencies, sensitive data in logs and
  errors that fail open. Every finding has a severity, its path:line, its CWE
  and its OWASP Top 10:2025 category, from a stable checklist that
  judge-security reuses. In the SDD verify
  phase from Tier 3 it writes the security_review gate; outside the cycle it
  reviews a PR or a branch and answers with the same content. Use it when a
  change reaches verify in Tier 3 or 4, or whenever someone asks for a
  security review of code. Triggers: "security review", "security review this
  PR", "review this diff for vulnerabilities", "is this change secure",
  "AppSec review", "check this code for injection", "OWASP review".
metadata:
  exo-pack: security
  exo-execution: inline
  exo-phase: verify
  exo-permissions: read-only+gate
---

# security-code-review

## Result

- A list of findings, each with a severity, its `path:line`, what is wrong with a suggested fix as text, and its rule: the check ID of `references/review-checklist.md` with its CWE and the OWASP Top 10:2025 category of that CWE, from `.exo/shared/owasp-2025.md`.
- In an SDD change, when the tier has the gate: `<change-root>/gates/security_review.md`, started from `.exo/shared/templates/gate.md`, and `exo speclint <change-root>` passes.
- Outside the cycle: the same content (Verdict, Findings, Approval) in the answer. No file is written.

## When it runs

| Situation | What it reviews | Where the result goes |
|---|---|---|
| SDD verify, when `security_review` is in the tier's gates (`governance.gates` in `.exo/config.json`; by default Tier 3 and 4) | the diff of the change | the gate file, and the same findings in `verify-record.md`, Issues Found |
| Someone asks for a security review of a PR, a branch or some files | that diff or those files | the answer |
| `judge-security` (pack `quality`) reviews a stage | it reuses `references/review-checklist.md` and cites its check IDs | the judge's findings |

A gate always runs its skill: in a tier that has `security_review`, this review runs even when the diff looks harmless, and then the gate says so with its single "No findings" row.

## Permissions

- **Read-only.** Read and search files, and run read-only git: `git diff`, `git log`, `git show`, `git status`.
- **Never:** edit a file, install anything, run the application, send requests to prove an exploit, or paste code or data from the diff into an external tool.
- **The only write** is the gate file, done by whoever records the result (below).
- **Never copy a secret or personal data** into a finding, the answer or the gate: point at `path:line`. If a real secret is in the diff, tell the person to remove it and to rotate it (`.exo/shared/data-protection.md`, section C).

## Who runs it

- **In the cycle,** where verify runs. With subagents, inside `sdd-verifier`, in fresh context: it returns the full gate text after the text of `verify-record.md` and before the envelope, and the orchestrator writes it verbatim to `<change-root>/gates/security_review.md`. Without subagents, the session that runs verify writes it, and declares the isolation as `.exo/shared/agent-capabilities.md` says.
- **Outside the cycle,** inline. Read the files in small batches and take notes as you go.
- **Independent:** judge the code, not the author's explanation. A PR description or a commit message is context, never evidence (`.exo/shared/judge-common.md`, section B).

## Scope

1. **The diff.** In a change, `git diff <target branch>...HEAD`, or the base the delegation gives. For a PR, `git diff <target branch>...<PR branch>`. Start with `git diff --stat` and note new entry points, configuration, manifests and lockfiles.
2. **Whole files.** Read each changed file in full, not only its hunks. Follow every new or changed input from its source (request, message, file, environment, third-party response) to its sinks (query, command, file path, HTML, outbound request, deserializer, log), one hop into callers and callees when the flow leaves the file.
3. **The plan, in a change.** Read spec.md and, when present, design.md, Risks & Mitigations. Each mitigation that lands in the changed code must be there; a missing one is a High finding ("mitigation missing", `.exo/shared/judge-common.md`, section D).
4. **Data.** When the diff handles personal data or credentials, or sends data out of the system, classify it with skill:data-classification before judging SCR-SECRET and SCR-LOG.
5. **In scope:** what the diff adds or changes, and old code the diff now exposes (a new caller of an unsafe helper, a route that newly reaches it). **Out of scope:** a vulnerability that exists without the diff. It goes in the answer as a follow-up with `path:line`, not in the gate.

## What to look for

Walk each category. The items, their signals and what is not a finding are in `references/review-checklist.md`.

| Category | What | OWASP 2025 | Main CWEs |
|---|---|---|---|
| SCR-INJ | Injection: SQL, NoSQL, OS command, LDAP, XPath, template and expression | A05:2025 Injection | CWE-89, CWE-943, CWE-78, CWE-94 |
| SCR-AUTHN | Broken authentication: entry points without authentication, tokens, sessions, brute force | A07:2025 Authentication Failures | CWE-306, CWE-287, CWE-384, CWE-307 |
| SCR-AUTHZ | Broken authorization: missing or wrong checks, object-level access, tenancy, CSRF, mass assignment | A01:2025 Broken Access Control | CWE-862, CWE-863, CWE-639, CWE-352 |
| SCR-SECRET | Exposed secrets: in code, config, URLs, responses or client bundles | A07:2025 Authentication Failures, A01:2025 Broken Access Control | CWE-798, CWE-540, CWE-200 |
| SCR-DESER | Unsafe deserialization and XML external entities | A08:2025 Software or Data Integrity Failures, A02:2025 Security Misconfiguration | CWE-502, CWE-611 |
| SCR-SSRF | Server-side request forgery | A01:2025 Broken Access Control | CWE-918 |
| SCR-PATH | Path traversal and unsafe file handling | A01:2025 Broken Access Control, A06:2025 Insecure Design | CWE-22, CWE-434 |
| SCR-XSS | Cross-site scripting | A05:2025 Injection | CWE-79 |
| SCR-DEP | Risky dependencies | A03:2025 Software Supply Chain Failures, A08:2025 Software or Data Integrity Failures | CWE-1395, CWE-1104, CWE-1357, CWE-494 |
| SCR-LOG | Sensitive data in logs, log injection, missing security logs | A09:2025 Security Logging and Alerting Failures | CWE-532, CWE-117, CWE-778 |
| SCR-CRYPTO | Weak cryptography and randomness | A04:2025 Cryptographic Failures | CWE-327, CWE-330, CWE-916, CWE-319 |
| SCR-ERR | Exceptional conditions: errors that leak details, fail open, are swallowed or go unchecked | A10:2025 Mishandling of Exceptional Conditions | CWE-209, CWE-636, CWE-755, CWE-252 |

The column names the categories most checks of a group fall in. A finding takes the category of its own CWE from `.exo/shared/owasp-2025.md`, written with its year, and the checklist marks the checks whose CWE falls elsewhere (a token without signature verification, CWE-347, is `A04:2025 Cryptographic Failures`).

## Confirm before reporting

- **Evidence:** a finding names the source, the sink and the missing control, with `path:line`. "Could be vulnerable" without a path from input to sink is not a finding.
- **Framework protections count.** The ORM's parameters, auto-escaping templates, the CSRF middleware, the authentication filter: no finding unless the diff bypasses them (a raw query helper, raw HTML output, an exemption list).
- **Reachability:** a sink that untrusted input cannot reach is hardening at most (Low).
- **Unsettled suspicion:** when the control may live where you cannot see it (an API gateway, another repository), report it with the severity it would have, start the finding with `Unconfirmed:` and say what would settle it. The person decides.

## Severity

On the levels of `.exo/shared/judge-common.md`, section D:

| Severity | For a security review |
|---|---|
| Critical | Exploitable as written, by an anonymous or low-privilege caller, with serious impact: injection into a query or command, data or actions without authentication or authorization, a real secret in the diff, untrusted data into an unsafe deserializer, SSRF to internal addresses, a path that escapes its folder |
| High | Exploitable under plausible conditions: object-level access that needs a valid account, stored XSS, tokens or personal data in logs, a known vulnerable dependency the code reaches, a mitigation from design.md missing |
| Medium | Defense in depth missing or unusual conditions needed: no attempt limit on login, a weak but not broken setting, detailed error messages, a missing security log |
| Low | Hardening with no attack path |

## Verdict

- `APPROVED` when no Critical or High finding is open.
- `ESCALATED` when one is, or when part of the diff could not be reviewed (generated code, binaries, a file too large, a language you cannot read): say what in the Verdict sentence.

## Write the gate

```markdown
# Gate: security_review

<!-- exo-gate:security_review -->

## Verdict

ESCALATED: one Critical finding open (order lookup without an ownership check).

## Findings

| Severity | File:line | Finding | Rule/OWASP |
|---|---|---|---|
| Critical | src/orders/api.py:57 | GET /orders/{id} loads any order by ID; the caller's ownership is never checked. Filter by the session's customer ID | SCR-AUTHZ-2, A01:2025, CWE-639 |
| Medium | src/orders/api.py:91 | The 500 response returns the exception text. Return a generic message and log the detail | SCR-ERR-1, A10:2025, CWE-209 |

## Approval

Requires tech_lead approval: yes
Source: skill security-code-review
```

- With no findings, the table has one row: `| None | — | No findings | — |`.
- The Rule/OWASP column always carries the check ID, then the OWASP Top 10:2025 category with its year and the CWE, so `judge-security` and the person can trace it.
- `Requires tech_lead approval` is `yes` when the verdict is `ESCALATED` or a Critical or High finding stays open, and `no` otherwise.
- In verify, list the same findings in `verify-record.md`, Issues Found (severity, `path:line`, impact, fix), so the verify Verdict counts them.

## After the review

1. Whoever records the result writes the gate file and runs `exo speclint <change-root>`. If it fails, the text goes back to the reviewer; never edit the findings or the verdict yourself.
2. The person decides each finding. Fixed: the change goes back to apply, then to verify, and this review runs again on the new diff. Not fixed: a gate that is not `APPROVED` needs the `tech_lead` role, who accepts the risk in the PR; record that decision as `"by": "human"`. In an unattended run, do not stop: leave it `ESCALATED` and say so.
3. `exo gate publish` turns the gate into one PR comment (`.exo/shared/ci-and-review.md`, section D).

## Record

Inline, before the envelope (`.exo/shared/capability-attribution.md`); in a subagent, report it in the notes and the orchestrator records it:

```bash
exo change record <change> --add capabilities_used '{"name": "security-code-review", "type": "skill", "activation": "auto", "resolution": "paths-injected"}'
exo change record <change> --add skills_used '"security-code-review"'
exo change record <change> --add gates '{"name": "security_review", "status": "fail", "detail": "1 Critical open: SCR-AUTHZ-2"}'
exo change record <change> --add decisions '{"summary": "security_review: SCR-ERR-1 accepted as is", "rationale": "the error page is internal-only", "by": "human"}'
```

The gate status is `pass` for `APPROVED` and `fail` for `ESCALATED`, and `waived` once the `tech_lead` accepts an `ESCALATED` gate; record it once the gate file is final.
