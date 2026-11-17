---
name: java-reviewer
description: >-
  Reviews Java and Kotlin code in Spring Boot and Quarkus projects,
  read-only: correctness, layering, JPA and Hibernate (also Panache) and
  MongoDB data access, transactions, security, concurrency, resource
  handling, error handling and tests. Detects the framework, reads the diff
  and the files around it, and returns findings with severity, path:line,
  the rule (with CWE and OWASP Top 10:2025 for security) and a suggested
  fix, plus a verdict. Never edits. Use it when someone asks for a review of
  Java or Kotlin code: a Java diff, a branch or a pull request of a JVM
  service. Not for the pre-commit check (pre-commit-review) or the SDD
  verify (sdd-verify). Triggers: "review this Java code", "review my Java
  changes", "Java code review", "review this Spring Boot pull request",
  "anything wrong with this Java class", "review this Kotlin diff".
metadata:
  exo-pack: java
  exo-execution: inline
  exo-permissions: read-only
---

# java-reviewer

## Result

A review of the Java and Kotlin files a diff touches: a findings table ordered by severity, each finding with its `path:line`, what is wrong, its rule (with the CWE and the OWASP Top 10:2025 category when it is a security finding) and a fix as text (a short snippet is fine); what was not reviewed; follow-ups outside the diff; and a last line `Verdict: approve` or `Verdict: request changes` (Verdict). You change nothing: no edits, no staging, no commits.

## When

- Someone asks for a review of Java or Kotlin code in a JVM service: the staged or uncommitted changes, a branch, a pull request, or files they name.
- **In SDD verify, on request:** when the person or the verify asks for a Java-specific review, as a complement to skill:harness-review. The gates still come from `harness-review` and `security-code-review`; this review adds the Java checks, and its Critical and High findings go to Issues Found of `verify-record.md`. Outside the phases, skill:backend-engineering routes review tasks here.
- **Not for:** the quick check before each commit (`pre-commit-review`, pack `quality`); the verify of an SDD change itself (`sdd-verify`, pack `sdd`); conventions only (skill:java-coding-standards); dependency vulnerabilities (skill:security-scan-jkp); a failing build (skill:java-build-resolver).

## Permissions

Read-only: read files and run read-only git (`git diff`, `git show`, `git log`, `git status`). Never edit, stage, stash or commit. If a finding needs a change, describe it.

## Inputs

1. **The diff:** staged (`git diff --staged`), the working tree (`git diff`, plus untracked files from `git status`), a branch (`git diff <base>...HEAD`) or the PR the person names. Ask which one only when it is ambiguous.
2. **The changed files in full,** not only the hunks, and the code they call: a repository method, an entity, the error handler, the security configuration.
3. **The tests** that cover the change, and the build file for the framework and the libraries.
4. `.exo/context.md` (conventions, risks) and, inside an SDD change, the spec and the tasks the change implements.

Read in batches and take notes as you go.

## Steps

1. **Detect the stack:** Spring Boot or Quarkus and its version; Spring MVC or WebFlux; JPA/Hibernate, Panache or MongoDB; Spring Security present or not; the migration tool.
2. **Understand the change:** what it adds or changes, which entry points (endpoints, consumers, scheduled jobs) reach it, and what data it touches.
3. **Apply the checklist** of `references/checklist.md`, category by category. The main points are below.
4. **Confirm** each finding (Confirm before reporting), rate it (Severity) and write the fix as text.
5. **Verdict.**

## What to look for

| Category | Rule | Main points |
|---|---|---|
| Correctness | JR-CORR | Logic against the spec and the domain rules; nulls and `Optional.get()`; off-by-one and boundaries; integer overflow; `BigDecimal.equals` versus `compareTo`; time zones and `LocalDate.now()` instead of the project's clock; a new path that bypasses rules the existing service enforces |
| Layering | JR-LAYER | Controllers calling repositories; entities returned by the API; business logic in controllers; new dependencies between packages that close a cycle |
| Data access | JR-DATA | N+1 (a query or a lazy relation inside a loop); unbounded `findAll()`; `FetchType.EAGER` on collections; JPQL, SQL or Mongo queries built by concatenation; missing indexes for new queries; a new column without its migration; an applied migration edited |
| Transactions | JR-TX | Writes without a transaction (changes never flushed); `@Transactional` on private methods or called from the same class (the proxy is bypassed); checked exceptions that do not roll back; remote calls inside a transaction; lost updates without `@Version` |
| Security | JR-SEC | Injection; missing authentication or object-level authorization; secrets in code or config; personal data in logs; unsafe deserialization; XXE; SSRF; path traversal; weak cryptography or randomness; errors that leak internals |
| Concurrency | JR-CONC | Mutable state in singleton beans; check-then-act without a lock or a constraint; non-thread-safe types shared (`SimpleDateFormat`); `@Async` or `CompletableFuture` on the default pool |
| Resources | JR-RES | Streams, connections and clients not closed (try-with-resources); HTTP clients without timeouts |
| Errors | JR-ERR | Swallowed exceptions; `catch (Exception)` that returns a default; lost causes; a business error that becomes a 500 |
| Tests | JR-TEST | New behavior without a test; tests that would pass without the behavior; `Thread.sleep`; `@SpringBootTest` where a slice would do; real clock or network |
| Conventions | JCS-n | Only when they hide a defect or the project's linter would fail; the full list is skill:java-coding-standards |

For security findings, cite the CWE and its OWASP Top 10:2025 category with its year, from `.exo/shared/owasp-2025.md` (`CWE-89, A05:2025 Injection`). For a deep security review of the same diff, skill:security-code-review applies.

## Confirm before reporting

- **Evidence:** a finding names what happens, where (`path:line`) and why it is wrong. For security, the source of the input, the sink and the missing control; "could be unsafe" without a path from input to sink is not a finding.
- **Framework protections count:** bound parameters in Spring Data and JPA, Jackson without default typing, Spring Security's CSRF protection for cookie sessions. No finding unless the diff bypasses them.
- **In scope:** what the diff adds or changes, and old code the diff now reaches. A problem that exists without the diff goes under Follow-ups, not in the table.
- **Unsettled:** when the control may live where you cannot see it (a gateway, another service), start the finding with `Unconfirmed:` and say what would settle it.

## Severity

| Severity | Meaning |
|---|---|
| Critical | exploitable by anyone who reaches the entry point (injection, an authorization bypass, a credential in code), data loss or corruption, the main flow broken |
| High | wrong behavior in a normal case, a write that is never saved, a domain rule bypassed, a lost update, personal data in logs, a missing authorization check behind sign-in |
| Medium | an edge case or error path, a swallowed exception, an N+1 or unbounded query that grows with the data, an entity exposed by the API |
| Low | readability, naming, conventions, harmless leftovers |

Never copy a secret or personal data into a finding: point at the `path:line`. Never raise or lower a severity to reach a verdict; the person decides what to fix.

## Verdict

- `Verdict: approve` when no finding is Critical or High.
- `Verdict: request changes` when one is, or when part of the diff that matters could not be reviewed (generated code, a file too large, code the diff calls that you could not read): say what under Not reviewed.

## Return

```markdown
# Java review: staged diff (3 files)

Stack: Spring Boot 3.4, JPA, Spring Security (pom.xml:12, pom.xml:31). Read in full: OrderService.java, OrderController.java, OrderServiceTest.java, and Product.java, which they call.

| # | Severity | path:line | Finding | Rule | Fix |
|---|---|---|---|---|---|
| 1 | Critical | src/main/java/com/example/orders/OrderService.java:58 | The customer name from the request is concatenated into a JPQL string | JR-SEC (CWE-89, A05:2025 Injection) | Use a named parameter: `where o.customerName = :name` with `setParameter` |
| 2 | High | src/main/java/com/example/orders/OrderService.java:71 | Stock is read, checked and decremented without a lock or a version, so two orders can take the last item | JR-CONC, JR-TX | Add `@Version` to Product and map the optimistic lock failure to 409, or use an atomic `update ... where stock > 0` |
| 3 | Medium | src/main/java/com/example/orders/OrderService.java:84 | One `findById` per line item inside the loop (N+1) | JR-DATA | Load the products with `findAllById(ids)` and map them |
| 4 | Low | src/main/java/com/example/orders/OrderService.java:20 | Field injection | JCS-11 | Constructor injection with a final field |

## Not reviewed

The OpenAPI contract (not in the diff).

## Follow-ups

- src/main/java/com/example/orders/OrderRepository.java:22 (not in the diff): `findAll()` with no page feeds the admin export.

Verdict: request changes
```

- Order the table by severity, Critical first. Number the rows; the Rule column holds the checklist rule, not the finding number.
- `path:line` points at the line that shows the problem; a whole-file finding (no test) points at the file or folder.

## Record

Inside an SDD change, an inline phase records the skill (`.exo/shared/capability-attribution.md`); a subagent lists it in its envelope notes:

```bash
exo change record <change> --add capabilities_used '{"name": "java-reviewer", "type": "skill", "activation": "requested", "resolution": "fallback-registry"}'
exo change record <change> --add skills_used '"java-reviewer"'
```

`activation` is `requested` when the person asked for the review and `auto` when a phase loaded it. Findings the person decides not to fix go to `dismissed_followups` with their reason, recorded by the orchestrator; never dismiss one yourself. In Windows PowerShell 5.1, pass the JSON as `'@<file>'` (`.exo/shared/sdd-phase-common.md`, section I).

## Before you finish

- [ ] You read the changed files in full and the code they call, not only the hunks.
- [ ] Every finding has a severity, `path:line`, a rule (CWE and OWASP Top 10:2025 with its year for security) and a fix.
- [ ] Data access, transactions, security and concurrency were checked, or listed under Not reviewed.
- [ ] Nothing outside the diff is in the table; it is under Follow-ups.
- [ ] No secret or personal data is copied into the answer.
- [ ] The last line is `Verdict: approve` or `Verdict: request changes`, following Verdict, and nothing was changed.
