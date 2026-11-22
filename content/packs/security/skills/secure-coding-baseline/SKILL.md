---
name: secure-coding-baseline
description: >-
  The minimum secure coding rules for every line of code the agent writes or
  changes, each tied to its CWE and OWASP Top 10:2025 category: validate and
  encode untrusted input at the boundary, parameterized queries,
  authentication and authorization on every entry point, fail closed, secrets
  from the environment or a secret manager, no secrets or personal data in
  logs, safe deserialization, vetted cryptography, errors that leak nothing,
  and dependency hygiene. Required in the SDD apply phase of every tier; in
  Tier 4 it also runs the secure_coding_check gate, a read-only review of the
  diff against these rules. Use it whenever you write or change code, and when
  someone asks whether code follows secure coding practice. Triggers: "secure
  coding", "write this securely", "is this code secure", "secure coding
  check", "OWASP rules", "harden this code", "sanitize the input".
metadata:
  exo-pack: security
  exo-execution: inline
  exo-phase: apply
---

# secure-coding-baseline

## Result

- The code written or changed in this session follows the ten rules below. Any rule you cannot follow is visible: a question to the person or a follow-up, never a silent gap.
- In Tier 4, `<change-root>/gates/secure_coding_check.md`, started from `.exo/shared/templates/gate.md`, and `exo speclint <change-root>` passes.
- Outside an SDD change, the rules apply to what you write. When someone asks you to check code against them, the gate content goes in the answer and no file is written.

## When it applies

- **SDD apply, every tier.** It is a Required skill of the apply row in `.exo/shared/phase-skill-map.md`, next to skill:code-generation. Read it in full before the first task.
- **Any code outside the cycle:** a quick fix, a script, a migration, a test helper.
- **Scope:** the lines the change adds or modifies and the paths those lines open (a new route, a new query, a new log line). A violation in code the change does not touch is a follow-up with `path:line`, not a fix: the scope rule of the project rules still holds.

## The rules

Each rule has a stable ID. Cite it in findings, follow-ups and gate rows. The detailed checks of each rule are in `references/checklist.md`, each with its CWE; the OWASP Top 10:2025 category of a CWE comes from `.exo/shared/owasp-2025.md`.

| ID | Rule | OWASP 2025 / CWE |
|---|---|---|
| SCB-1 | **Validate and encode untrusted input at the boundary.** Everything from outside the process is untrusted: request fields, headers, cookies, files, messages, environment, third-party responses. Validate type, length, range and format against an allow-list on the server, and reject what fails. Encode output for the context it lands in (HTML, attribute, URL, JavaScript, shell, log) with the framework's encoder. | A05:2025 Injection (CWE-20, CWE-79, CWE-116) |
| SCB-2 | **Parameterized queries.** Bind parameters for SQL and NoSQL queries, LDAP filters and similar interpreters. Run processes with an argument list, never through a shell with interpolated input. No query or command built by concatenation or string formatting. | A05:2025 Injection (CWE-89, CWE-78, CWE-90) |
| SCB-3 | **Authentication and authorization on every entry point.** Every route, handler, consumer, scheduled job and CLI command that reads or changes data checks who calls and whether that caller may act on that specific object, on the server, deny by default. | A01:2025 Broken Access Control (CWE-862, CWE-863, CWE-639); A07:2025 Authentication Failures (CWE-306) |
| SCB-4 | **Fail closed.** On an error, a timeout, missing configuration or an unknown state, deny and stop. An exception inside a security check means "denied", never "allowed". | A10:2025 Mishandling of Exceptional Conditions (CWE-636, CWE-755) |
| SCB-5 | **Secrets from the environment or a secret manager.** Never in code, tests, committed config, URLs or error messages. Read them at runtime by name; document the name, never the value. | A07:2025 Authentication Failures (CWE-798); A04:2025 Cryptographic Failures (CWE-321) |
| SCB-6 | **No secrets or personal data in logs.** Log what happened and a non-personal reference (an internal request ID), never tokens, passwords, card or account numbers, national IDs, emails or free text written by people. Neutralize line breaks in logged input. Security events (failed logins, denied access) are logged, without the data. | A09:2025 Security Logging and Alerting Failures (CWE-532, CWE-117, CWE-778); A01:2025 Broken Access Control (CWE-359) |
| SCB-7 | **Safe deserialization.** Never deserialize untrusted data with a format that can create arbitrary types (native object serialization, unsafe YAML loaders, polymorphic type handling). Use data-only formats with a schema, and turn off XML external entities. | A08:2025 Software or Data Integrity Failures (CWE-502); A02:2025 Security Misconfiguration (CWE-611) |
| SCB-8 | **Cryptography only with vetted libraries.** Use the platform's or a well-known library's high-level API; never your own algorithm or mode. No MD5 or SHA-1 for security, passwords with a slow adaptive hash (Argon2, bcrypt, scrypt, PBKDF2), tokens from a cryptographically secure random generator, TLS with certificate validation on. | A04:2025 Cryptographic Failures (CWE-327, CWE-330, CWE-916); A07:2025 Authentication Failures (CWE-295) |
| SCB-9 | **Errors that leak nothing.** The caller gets a generic message and a reference; stack traces, queries, file paths, versions and internal names stay in the server log, which follows SCB-6. | A10:2025 Mishandling of Exceptional Conditions (CWE-209) |
| SCB-10 | **Dependency hygiene.** Add a dependency only when the plan names it: maintained, from the official registry, pinned through the lockfile, without known high or critical vulnerabilities. Never download and run code without an integrity check. | A03:2025 Software Supply Chain Failures (CWE-1104, CWE-1395, CWE-1357); A08:2025 Software or Data Integrity Failures (CWE-494) |

## While you write code

1. Before each task, find the entry points and the sinks it touches: where input comes in (routes, consumers, files) and where it ends up (queries, commands, file paths, HTML, outbound requests, deserializers, logs).
2. Follow the project's existing security helpers first: its validation layer, its authorization middleware, its ORM, its logger with masking. A new helper only when the plan names it.
3. Write the negative test next to the positive one when a rule is in play: the rejected input, the denied caller, the error that says nothing. In Tier 4, skill:test-strategy already asks for a negative test per risk of `design.md`.
4. Test data is synthetic (`.exo/shared/data-protection.md`, section C): placeholders such as `${DB_PASSWORD}` or `<your-token>`, `example.com` addresses, published test card numbers.
5. When the data the code handles is personal data or credentials, or it leaves the system, apply skill:data-classification. When logs, tickets or production data have to reach the model, apply skill:prompt-hygiene first.

**When a rule cannot be followed** (the legacy layer only accepts a raw query, the plan forgets an authorization check, a needed library is not in the plan): stop before writing the code and return `status: needs-input` with the rule ID, the reason and what you propose. Never weaken a rule to finish a task.

## The secure_coding_check gate (Tier 4)

Runs when the tier's gates in `.exo/config.json` (`governance.gates`) include `secure_coding_check`, which by default is Tier 4. A gate always runs its skill.

**When:** after the last apply task, over the full diff of the change; and again every time apply runs after a `needs-rework`, so the gate describes the diff that goes to the PR. `exo check` requires the file once `verify-record.md` exists.

**How:**

1. Get the diff from the merge base: `git diff <target branch>...HEAD`, plus `git status` to confirm nothing is left uncommitted.
2. Make a **read-only pass**: change nothing while it runs. Read each changed file around its hunks, follow each new input to its sinks, and check every added or modified line against SCB-1 to SCB-10 with `references/checklist.md`.
3. Each finding gets a severity, the `path:line`, what is wrong with a suggested fix, and its rule (`SCB-n` with its CWE and the OWASP Top 10:2025 category of that CWE, written with its year). Never copy a secret or personal data into a finding: point at the location.
4. **Fix loop.** A finding in code this change wrote goes back to its task: test first, fix inside the plan, commit, then repeat the pass. A finding the plan cannot fix (it needs a file, a dependency or a decision outside the plan) stays in the gate, and the apply returns `needs-input`.
5. Write the gate from the template.

**Severity**, on the levels of `.exo/shared/judge-common.md`, section D:

| Severity | For this gate |
|---|---|
| Critical | Exploitable as written: input reaching a query or command, data or actions without an authorization check, a secret in the diff, untrusted data into an unsafe deserializer |
| High | A rule broken with a plausible attack path, or a mitigation from `design.md`, Risks & Mitigations, missing |
| Medium | Defense in depth missing: an unvalidated field that is only stored, a detailed error message, a missing security log |
| Low | Hardening with no attack path: a stricter type, a narrower allow-list |

**Verdict:** `APPROVED` when no Critical or High finding is open. `ESCALATED` when one is, or when part of the diff could not be checked (generated code, binaries, a language you cannot read): say what in the Verdict sentence.

**Who writes the file:** with subagents, `sdd-implementer` returns the full gate text in its answer, before the envelope, and the orchestrator writes it verbatim; inline, the session writes it. Then `exo speclint <change-root>` must pass.

```markdown
# Gate: secure_coding_check

<!-- exo-gate:secure_coding_check -->

## Verdict

ESCALATED: one High finding stays open; it needs a dependency outside the plan.

## Findings

| Severity | File:line | Finding | Rule/OWASP |
|---|---|---|---|
| High | src/reports/export.py:88 | The PDF renderer fetches any URL in the template; restrict it to the asset folder (needs the renderer option the plan does not include) | SCB-1, A01:2025, CWE-918 |
| Medium | src/reports/api.py:41 | The error response includes the exception text; return a generic message and log the detail | SCB-9, A10:2025, CWE-209 |

## Approval

Requires tech_lead approval: yes
Source: skill secure-coding-baseline
```

With no findings, the table has one row: `| None | — | No findings | — |`. `Requires tech_lead approval` is `yes` when the verdict is `ESCALATED` or a Critical or High finding stays open, and `no` otherwise. A gate that is not `APPROVED` needs the `tech_lead` role; in an unattended run, do not stop: leave it `ESCALATED` and say so. `exo gate publish` turns it into a PR comment (`.exo/shared/ci-and-review.md`, section D).

## Record

Inline, before the envelope (`.exo/shared/capability-attribution.md`); in a subagent, report it in the notes and the orchestrator records it:

```bash
exo change record <change> --add capabilities_used '{"name": "secure-coding-baseline", "type": "skill", "activation": "auto", "resolution": "paths-injected"}'
exo change record <change> --add skills_used '"secure-coding-baseline"'
exo change record <change> --add gates '{"name": "secure_coding_check", "status": "pass"}'
```

The gate status is `pass` for `APPROVED` and `fail` for `ESCALATED`, and `waived` once the `tech_lead` accepts an `ESCALATED` gate; record it once the gate file is final. Follow-ups you found outside the scope go in the envelope notes with `path:line` (skill:ai-usage-record).
